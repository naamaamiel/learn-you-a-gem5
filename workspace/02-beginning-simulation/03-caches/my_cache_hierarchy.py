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

# Our L3 cache with custom parameters
class L3Cache(Cache):
    def __init__(self, size, assoc):
        # Step 1: Fill in the constructor

# Our custom cache hierarchy
class PrivateL1PrivateL2SharedL3CacheHierarchy(AbstractClassicCacheHierarchy):
    def __init__(self, l1d_size, l1i_size, l2_size, l3_size, l1d_assoc=8, l1i_assoc=8, l2_assoc=16, l3_assoc=32):
        AbstractClassicCacheHierarchy.__init__(self)
        self._l1d_size = l1d_size
        self._l1i_size = l1i_size
        self._l2_size = l2_size
        self._l3_size = l3_size
        self._l1d_assoc = l1d_assoc
        self._l1i_assoc = l1i_assoc
        self._l2_assoc = l2_assoc
        self._l3_assoc = l3_assoc

        # Step 2: Set up the membus


    # Step 3: Define getters for the mem- and CPU- side ports
    def get_mem_side_port(self):
        pass
    
    def get_cpu_side_port(self):
        pass


    # Step 4: Fill in incorporate_cache
    def incorporate_cache(self, board):
        # Connect system port to CPU

    
        # Connect memory ports to memory

        
        # Instantiate and connect the L3 cache


        # (After completing _create_core_cluster) Instantiate and connect the core clusters


        # I/O things
        if board.has_coherent_io():
            self._setup_io_cache(board)
    
    # Step 5: Core clusters
    def _create_core_cluster(self, core, l3_bus, isa):
        # Instantiate cluster subsystem and the L1 caches


        # Connect the L1 caches to the core


        # YOUR TURN: Create and connect the L2 cache and crossbar
        # a) Create the L2 cache and crossbar
        

        # b) Connect the L1I and L1D caches to the L2 crossbar
       

        # c) Connect the L2 cache to the L2 and L3 crossbars
        

        # Full-system mode magic
        cluster.iptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        cluster.dptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        core.connect_walker_ports(
            cluster.iptw_cache.cpu_side, cluster.dptw_cache.cpu_side
        )
        
        cluster.iptw_cache.mem_side = cluster.l2_bus.cpu_side_ports
        cluster.dptw_cache.mem_side = cluster.l2_bus.cpu_side_ports

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