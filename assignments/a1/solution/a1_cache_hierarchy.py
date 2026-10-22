"""
Assignment #1: Assemble-Your-Own-System

Custom cache hierarchy component

Name: Solution
"""
from gem5.isas import ISA
from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import AbstractClassicCacheHierarchy
from gem5.components.cachehierarchies.classic.caches.l1icache import L1ICache
from gem5.components.cachehierarchies.classic.caches.l1dcache import L1DCache
from gem5.components.cachehierarchies.classic.caches.l2cache import L2Cache
from gem5.components.cachehierarchies.classic.caches.mmu_cache import MMUCache


from m5.objects import (
    BadAddr,
    Cache,
    SystemXBar,
    SubSystem,
    L2XBar
)

class L3Cache(Cache):
    def __init__(self, size, assoc):
        super().__init__()
        self.size = size
        self.assoc = assoc
        self.tag_latency = 20
        self.data_latency = 20
        self.response_latency = 1
        self.mshrs = 20
        self.tgts_per_mshr = 12

# Our custom cache hierarchy
class CustomCacheHierarchy(AbstractClassicCacheHierarchy):
    def __init__(self, l1d_size, l1i_size, l2_size, l3_size, l1d_assoc=2, l1i_assoc=2, l2_assoc=8, l3_assoc=16):
        AbstractClassicCacheHierarchy.__init__(self)
        self._l1d_size = l1d_size
        self._l1i_size = l1i_size
        self._l2_size = l2_size
        self._l3_size = l3_size
        self._l1d_assoc = l1d_assoc
        self._l1i_assoc = l1i_assoc
        self._l2_assoc = l2_assoc
        self._l3_assoc = l3_assoc

        self.membus = SystemXBar(width=64)

        self.membus.badaddr_responder = BadAddr()
        self.membus.default = self.membus.badaddr_responder.pio

    def get_mem_side_port(self):
        return self.membus.mem_side_ports

    def get_cpu_side_port(self):
        return self.membus.cpu_side_ports

    def _create_core_cluster(self, core, l2_bus, isa):
        cluster = SubSystem()
        cluster.l1dcache = L1DCache(
        size=self._l1d_size, 
        assoc=self._l1d_assoc
        )
        cluster.l1icache = L1ICache(
            size=self._l1i_size, 
            assoc=self._l1i_assoc,
            writeback_clean=False
        )

        core.connect_icache(cluster.l1icache.cpu_side)
        core.connect_dcache(cluster.l1dcache.cpu_side)

        cluster.l1dcache.mem_side = l2_bus.cpu_side_ports
        cluster.l1icache.mem_side = l2_bus.cpu_side_ports

        cluster.iptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        cluster.dptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        core.connect_walker_ports(
            cluster.iptw_cache.cpu_side, cluster.dptw_cache.cpu_side
        )
        
        cluster.iptw_cache.mem_side = l2_bus.cpu_side_ports
        cluster.dptw_cache.mem_side = l2_bus.cpu_side_ports

        if isa == ISA.X86:
            int_req_port = self.membus.mem_side_ports
            int_resp_port = self.membus.cpu_side_ports
            core.connect_interrupt(int_req_port, int_resp_port)
        else:
            core.connect_interrupt()
        
        return cluster

    def incorporate_cache(self, board):
        board.connect_system_port(self.membus.cpu_side_ports)
    
        for _, port in board.get_memory().get_mem_ports():
            self.membus.mem_side_ports = port

        self.l2_bus = L2XBar()
        self.l3_bus = L2XBar()

        self.l2_cache = L2Cache(size=self._l2_size, assoc=self._l2_assoc)
        self.l2_cache.mem_side = self.l3_bus.cpu_side_ports
        self.l2_cache.cpu_side = self.l2_bus.mem_side_ports
        
        self.l3_cache = L3Cache(size=self._l3_size, assoc=self._l3_assoc)
        self.l3_cache.mem_side = self.membus.cpu_side_ports
        self.l3_cache.cpu_side = self.l3_bus.mem_side_ports

        # Instantiate and connect the core clusters
        self.clusters = [
            self._create_core_cluster(
                core, self.l2_bus, board.get_processor().get_isa()
            )
            for core in board.get_processor().get_cores()
        ]

        # I/O things
        if board.has_coherent_io():
            self._setup_io_cache(board)

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
