from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING

import torch

from lplb._cpp import CompiledSolver
from lplb.eplb import rebalance_experts


if TYPE_CHECKING:
    from deep_ep import Buffer


@functools.lru_cache(maxsize=None)
def _get_solver(
    n_group: int,
    group_size: int,
    dup_per_rank: int,
    n_local_experts: int,
    n_combined_experts: int,
    ep_group: torch.distributed.ProcessGroup,
) -> CompiledSolver:
    return CompiledSolver(
        str(Path(__file__).parent / 'resources'),
        n_group,
        group_size,
        dup_per_rank,
        256,
        n_local_experts,
        n_combined_experts,
        ep_group,
    )


class Planner:
    def __init__(
        self,
        redundant_to_original: torch.Tensor,
        n_routed_experts: int,
        n_logical_routed_experts: int,
        ep_size: int | None = None,
        group: torch.distributed.ProcessGroup | None = None,
    ) -> None:
        """
        :param redundant_to_original: [group_size, num_redundants]
            Mapping from redundant experts to their original indices.

            For convenience, LP requires redundant experts to follow a specific structure:

            1. Each rank has the same number of redundant experts.
            2. The i-th redundant expert on any rank must be a copy of the i-th expert on another rank.

            This ensures that each redundant expert is shared between exactly two ranks.

            As an extension, the actual number of redundant experts can be a multiple of `num_redundants`,
            allowing multiple redundant experts to be grouped for weight distribution.

        :param n_routed_experts: Total number of physical routed experts (including redundants).
        :param n_logical_routed_experts: Total number of logical routed experts.
        :param ep_size: Total number of EP ranks. Defaults to `group.size()`. Must be provided if `group` is None.
        :param group: EP communication group. Defaults to None, meaning no workload reduction is performed.
        """
        # C5: Add comprehensive input validation
        if not isinstance(redundant_to_original, torch.Tensor):
            raise ValueError("redundant_to_original must be a torch.Tensor")
        if redundant_to_original.dim() != 2:
            raise ValueError(f"redundant_to_original must be 2D, got {redundant_to_original.dim()}D")
        if redundant_to_original.shape[0] <= 0 or redundant_to_original.shape[1] <= 0:
            raise ValueError(f"redundant_to_original shape must be positive, got {redundant_to_original.shape}")
        if redundant_to_original.max() >= n_logical_routed_experts:
            raise ValueError(f"redundant_to_original contains indices >= n_logical_routed_experts ({n_logical_routed_experts})")
        if redundant_to_original.min() < 0:
            raise ValueError("redundant_to_original contains negative indices")
        
        # Validate expert counts to prevent integer overflow
        if n_routed_experts <= 0 or n_routed_experts > 1e7:  # Reasonable upper limit
            raise ValueError(f"n_routed_experts must be positive and reasonable, got {n_routed_experts}")
        if n_logical_routed_experts <= 0 or n_logical_routed_experts > 1e7:
            raise ValueError(f"n_logical_routed_experts must be positive and reasonable, got {n_logical_routed_experts}")
        if n_routed_experts < n_logical_routed_experts:
            raise ValueError(f"n_routed_experts ({n_routed_experts}) must be >= n_logical_routed_experts ({n_logical_routed_experts})")
        
        # Use int64 to prevent overflow, validate before converting
        if redundant_to_original.dtype.is_floating_point:
            redundant_to_original = redundant_to_original.long()
        self.r2o = redundant_to_original.long().cuda()  # Use long instead of int to prevent overflow
        self.o2r = self.r2o.argsort(dim=0).long().contiguous()  # Use long instead of int
        self.group_size, self.num_redundants = self.r2o.shape[0], self.r2o.shape[1]

        self.n_routed_experts = n_routed_experts
        self.n_logical_routed_experts = n_logical_routed_experts
        if ep_size is not None:
            self.ep_size = ep_size
        else:
            assert group is not None, 'ep_size must be provided when group is None'
            self.ep_size = group.size()
        # n_group is calculated based on the redundancy topology.
        # TODO: Should we check the relationship between routing groups, redundancy groups,
        # and physical groups (NVLink)? Warn for special cases.
        self.n_group = self.ep_size // self.group_size

        self.n_local_routed_experts = self.n_routed_experts // self.ep_size
        self.n_local_logical_routed_experts = self.n_logical_routed_experts // self.ep_size
        # Combine redundant experts into `self.r2o.shape[1]` groups for LP solving.
        self.combined_redundant_experts = (
            self.n_local_routed_experts - self.n_local_logical_routed_experts
        ) // self.num_redundants

        # Default phy2log mapping for use when no reordering is applied.
        self.phy2log: torch.Tensor
        self.update_redundancy_mapping()

        self.ep_group = group
        self.deep_ep_initialized = False
        self.solver = _get_solver(
            self.n_group,
            self.group_size,
            self.num_redundants,
            self.n_local_routed_experts,
            self.combined_redundant_experts,
            self.ep_group,
        )

    def init_from_deep_ep(self, buffer: Buffer) -> None:
        if self.deep_ep_initialized:
            return

        self.deep_ep_initialized = True
        self.solver.init_comm(
            torch.device('cuda'),
            not buffer.low_latency_mode,
            buffer.num_rdma_bytes == 0,
        )

    def update_redundancy_mapping(
        self, workload: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # Use workload's device if provided, otherwise default to cuda
        if workload is not None:
            device = workload.device
            # Ensure workload is on CUDA for proper processing
            if device.type != 'cuda':
                workload = workload.cuda()
                device = workload.device
        else:
            device = 'cuda'
        
        # "nored": No redundancy. Run EPLB without redundancy.
        if workload is None:
            nored_phy2log = torch.arange(
                self.n_logical_routed_experts,
                device=device,
                dtype=torch.int32,
            )
        else:
            nored_phy2log, _, _ = tuple(
                x.squeeze(0).to(dtype=torch.int32, device=device)
                for x in rebalance_experts(
                    workload.unsqueeze(0),
                    self.n_logical_routed_experts,
                    self.n_group,
                    max(1, self.ep_size // torch.cuda.device_count()),
                    self.ep_size,
                )
            )
        nored_phy2log = nored_phy2log.reshape(
            self.n_group,
            self.group_size,
            self.n_local_logical_routed_experts,
        )
        if workload is not None:
            # Sort experts on each device by workload history.
            nored_phy2log = nored_phy2log.gather(
                dim=-1,
                index=workload[nored_phy2log].argsort(dim=-1, descending=True),
            )
        # "tored": To be made redundant.
        # Select the top `combined_redundant_experts * num_redundants` experts on each device.
        tored_log_ori = nored_phy2log[
            :, :, : self.combined_redundant_experts * self.num_redundants
        ].reshape(
            self.n_group,
            self.group_size,
            self.combined_redundant_experts,
            self.num_redundants,
        )
        tored_log_dup = tored_log_ori.gather(
            dim=1,
            index=self.r2o.long().unsqueeze(1).expand_as(tored_log_ori),
        )
        phy2log = torch.cat([nored_phy2log, tored_log_dup.flatten(2)], dim=-1).flatten()
        assert phy2log.shape[0] == self.n_routed_experts

        log2phy = [[] for _ in range(self.n_logical_routed_experts)]
        # Transpose phy2log before inserting into log2phy to ensure original experts precede copies.
        for phy_local, logs in enumerate(phy2log.reshape(self.ep_size, -1).T):
            for phy_ep_rank, log in enumerate(logs):
                log_idx = int(log)
                # Critical bounds check to prevent array index out of bounds
                assert 0 <= log_idx < len(log2phy), f"Logical expert index {log_idx} out of bounds [0, {len(log2phy)})"
                log2phy[log_idx].append(phy_ep_rank * self.n_local_routed_experts + phy_local)

        logcnt = torch.tensor([len(x) for x in log2phy], dtype=torch.int32, device=device)
        max_logcnt = int(logcnt.max())
        assert max_logcnt == 2
        log2phy = torch.tensor(
            [x + [-1] * (max_logcnt - len(x)) for x in log2phy],
            dtype=torch.int32,
            device=device,
        )

        self.phy2log = phy2log

        return phy2log, log2phy, logcnt

    def count_workload(self, idx: torch.Tensor, n_sms: int) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Count expert indices in `idx`, which may include -1 (ignored).
        Values must be in [-1, self.n_logical_routed_experts).

        :param idx: Selected logical expert indices (range: [-1, n_logical_routed_experts)).
        :param n_sms: Number of CUDA streaming multiprocessors used.
        :return: A tuple where the first element is the count result (shape: (n_logical_routed_experts,)),
                 and the second is an intermediate result (shape: (n_sms, n_logical_routed_experts)).
        """
        # M4: Add input sanitization
        if not isinstance(idx, torch.Tensor):
            raise ValueError("idx must be a torch.Tensor")
        if idx.dtype not in [torch.int32, torch.int64, torch.long]:
            raise ValueError(f"idx must be integer tensor, got {idx.dtype}")
        if n_sms <= 0 or n_sms > 512:  # Reasonable GPU SM limit
            raise ValueError(f"n_sms must be positive and reasonable (1-512), got {n_sms}")
        
        # Validate idx values are within expected range
        if idx.numel() > 0:  # Only check if tensor is not empty
            idx_min, idx_max = idx.min().item(), idx.max().item()
            if idx_min < -1:
                raise ValueError(f"idx contains values < -1: min={idx_min}")
            if idx_max >= self.n_logical_routed_experts:
                raise ValueError(f"idx contains values >= n_logical_routed_experts ({self.n_logical_routed_experts}): max={idx_max}")
        
        try:
            return self.solver.count_idx(idx, n_sms, 256)
        except Exception as e:
            raise RuntimeError(f"CUDA kernel count_idx failed: {e}")

    def solve_probs(
        self,
        workload: torch.Tensor,
        avail_counter: torch.Tensor,
    ) -> torch.Tensor:
        """
        Run the linear programming algorithm based on workload statistics to compute
        the load distribution ratio for each original redundant expert.

        :param workload: Workload statistics (numel = n_experts).
        :param avail_counter: Feasible solution counter (numel = 1).
        :return: Load distribution ratio (shape: (num_redundants, combined_redundant_experts)).
        """
        # H9: Add comprehensive error handling for CUDA operations
        try:
            # Input validation
            if not isinstance(workload, torch.Tensor):
                raise ValueError("workload must be a torch.Tensor")
            if not isinstance(avail_counter, torch.Tensor):
                raise ValueError("avail_counter must be a torch.Tensor")
            if workload.numel() == 0:
                raise ValueError("workload tensor is empty")
            if avail_counter.numel() != 1:
                raise ValueError(f"avail_counter must have exactly 1 element, got {avail_counter.numel()}")
            
            # Check for NaN/Inf values that could cause solver issues
            if torch.isnan(workload).any():
                raise ValueError("workload contains NaN values")
            if torch.isinf(workload).any():
                raise ValueError("workload contains Inf values")
            
            workload = workload.view(
                self.n_group,
                self.group_size,
                self.n_local_logical_routed_experts,
            )
            
            if self.ep_group is not None and not self.deep_ep_initialized:
                workload = workload.clone()
                # Ensure device synchronization before distributed operation to prevent races
                if workload.is_cuda:
                    torch.cuda.synchronize(workload.device)
                try:
                    torch.distributed.all_reduce(workload, group=self.ep_group)
                    # Synchronize after distributed operation to ensure completion
                    if workload.is_cuda:
                        torch.cuda.synchronize(workload.device)
                except Exception as e:
                    raise RuntimeError(f"Distributed all_reduce failed: {e}")
            
            result = self.solver.solve(workload, self.r2o, self.phy2log, avail_counter)
            
            # Validate solver output
            if torch.isnan(result).any():
                raise RuntimeError("LP solver returned NaN values - solver may have failed")
            if torch.isinf(result).any():
                raise RuntimeError("LP solver returned Inf values - solver may have failed")
                
            return result
            
        except torch.cuda.OutOfMemoryError as e:
            raise RuntimeError(f"CUDA out of memory in solve_probs: {e}")
        except Exception as e:
            raise RuntimeError(f"Error in solve_probs: {e}")

    def weighted_select_target(
        self,
        idx: torch.Tensor,
        o_weight: torch.Tensor,
        local_workload_by_sm: torch.Tensor,
        n_sms: int,
    ) -> torch.Tensor:
        """
        Select target experts based on the load distribution ratio.

        :param idx: Selected logical expert indices (range: [-1, n_logical_routed_experts)).
        :param o_weight: Load distribution ratio (shape: (num_redundants, combined_redundant_experts)).
        :param local_workload_by_sm: Prefix sum of workload per SM (from `count_idx`).
        :param n_sms: Number of CUDA streaming multiprocessors used.
        :return: Mapped physical expert indices (same shape as `idx`, range: [-1, n_routed_experts)).
        """
        return self.solver.map_idx(
            idx,
            o_weight,
            local_workload_by_sm,
            self.o2r,
            self.phy2log,
            n_sms,
            256,
        )

    def run(
        self,
        idx: torch.Tensor,
        avail_counter: torch.Tensor,
        n_sms: int | None = None,
    ) -> torch.Tensor:
        """
        Assign physical expert indices to the given logical expert indices.

        :param idx: Selected logical expert indices (range: [-1, n_logical_routed_experts)).
        :param avail_counter: Counter of available physical expert indices (shape: (n_routed_experts,)).
        :param n_sms: Number of CUDA streaming multiprocessors used.
        :return: Mapped physical expert indices (same shape as `idx`, range: [-1, n_routed_experts)).
        """
        if n_sms is None:
            n_sms = torch.cuda.get_device_properties(
                torch.cuda.current_device()
            ).multi_processor_count

        local_workload, local_workload_by_sm = self.count_workload(idx, n_sms)
        o_weight, _global_workload = self.solve_probs(local_workload, avail_counter)
        return self.weighted_select_target(idx, o_weight, local_workload_by_sm, n_sms)
