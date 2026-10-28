from typing import Optional, Sequence, Tuple, Union, Type

from m5.objects import (
    AddrRange,
    DRAMInterface,
    PacketEncryptor,
    Port,
)

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.memory.memory import ChanneledMemory
from gem5.utils.override import overrides

class EncryptedMemory(ChanneledMemory):
    def __init__(
        self,
        dram_interface_class: Type[DRAMInterface],
        num_channels: Union[int, str],
        interleaving_size: Union[int, str],
        size: Optional[str] = None,
        addr_mapping: Optional[str] = None,
        encryption_buffer_entries: int = 16,
        decryption_buffer_entries: int = 32,
        request_buffer_entries: int = 8,
        response_buffer_entries: int = 8,
        enc_dec_window: int = 2,
        num_enc_dec_units: int = 3,
        enc_dec_latency: int = 4
    ) -> None:

        super().__init__(
            dram_interface_class,
            num_channels,
            interleaving_size,
            size=size,
            addr_mapping=addr_mapping,
        )
        self.encryptors = [
            PacketEncryptor(
                encryption_buffer_entries=encryption_buffer_entries,
                decryption_buffer_entries=decryption_buffer_entries,
                request_buffer_entries=request_buffer_entries,
                response_buffer_entries=response_buffer_entries,
                window=enc_dec_window,
                num_units=num_enc_dec_units,
                enc_dec_latency=enc_dec_latency
            )
            for _ in range(num_channels)
        ]

    @overrides(ChanneledMemory)
    def incorporate_memory(self, board: AbstractBoard) -> None:
        super().incorporate_memory(board)
        for encryptor, ctrl in zip(self.encryptors, self.mem_ctrl):
            encryptor.mem_side_port = ctrl.port

    @overrides(ChanneledMemory)
    def get_mem_ports(self) -> Sequence[Tuple[AddrRange, Port]]:
        return [
            (ctrl.dram.range, encryptor.cpu_side_port)
            for ctrl, encryptor in zip(self.mem_ctrl, self.encryptors)
        ]
