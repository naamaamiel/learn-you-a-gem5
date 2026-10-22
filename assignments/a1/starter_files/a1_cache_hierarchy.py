"""
Assignment #1: Assemble-Your-Own-System

Custom cache hierarchy component

Name: 
"""

from gem5.isas import ISA
from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import AbstractClassicCacheHierarchy
from gem5.components.cachehierarchies.classic.caches.mmu_cache import MMUCache


from m5.objects import (
    Cache,
    SubSystem
)

class PrivateL1SharedL2SharedL3CacheHierarchy(AbstractClassicCacheHierarchy):
    def __init__(self,):
        self.membus = SystemXBar(width=64)
        
        self.membus.badaddr_responder = BadAddr()
        self.membus.default = self.membus.badaddr_responder.pio

    def get_mem_side_port(self):
        pass
    
    def get_cpu_side_port(self):
        pass

    def incorporate_cache(self, board):
        


        # I/O things
        if board.has_coherent_io():
            self._setup_io_cache(board)
    
    def _create_core_cluster(self, core, isa,):
      cluster = SubSystem()

      # Full-system mode magic
      cluster.iptw_cache = MMUCache(size="8KiB", writeback_clean=False)
      cluster.dptw_cache = MMUCache(size="8KiB", writeback_clean=False)
      core.connect_walker_ports(
          cluster.iptw_cache.cpu_side, cluster.dptw_cache.cpu_side
      )
      
      cluster.iptw_cache.mem_side = l2_bus.cpu_side_ports # NOTE: l2_bus is not declared; consider where it is appropriate to do so
      cluster.dptw_cache.mem_side = l2_bus.cpu_side_ports # NOTE: l2_bus is not declared; consider where it is appropriate to do so

      if isa == ISA.X86:
          int_req_port = self.membus.mem_side_ports
          int_resp_port = self.membus.cpu_side_ports
          core.connect_interrupt(int_req_port, int_resp_port)
      else:
          core.connect_interrupt()
    
      return cluster

    def _setup_io_cache(self, board) -> None:
        """Create a cache for coherent I/O connections"""
        self.iocache = Cache(
            assoc=8,
            tag_latency=50,
            data_latency=50,
            response_latency=50,
            mshrs=20,
            size="1KiB",
            tgts_per_mshr=12,
            addr_ranges=board.mem_ranges,
        )
        self.iocache.mem_side = self.membus.cpu_side_ports
        self.iocache.cpu_side = board.get_mem_side_coherent_io_port()
