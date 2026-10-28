from m5.objects.ClockedObject import ClockedObject
from m5.params import *


class PacketEncryptor(ClockedObject):
    type = "PacketEncryptor"
    cxx_header = "bootcamp/packet-encryptor/packet_encryptor.hh"
    cxx_class = "gem5::PacketEncryptor"

    cpu_side_port = ResponsePort(
        "ResponsePort to received requests from CPU side."
    )
    mem_side_port = RequestPort(
        "RequestPort to send received requests to memory side."
    )

    encryption_buffer_entries = Param.Int(
        "Number of entries in the encryption buffer."
    )
    decryption_buffer_entries = Param.Int(
        "Number of entries in the decryption buffer."
    )

    request_buffer_entries = Param.Int(
        "Number of entries in the outgoing request buffer."
    )
    response_buffer_entries = Param.Int(
        "Number of entries in the outgoing response buffer."
    )

    window = Param.Int(
        "Number of packets to attempt to encrypt/decrypt each cycle."
    )
    num_units = Param.Int(
        "Number of encryption and decryption units."
    )
    enc_dec_latency = Param.Cycles(
        "Encryption/decryption latency."
    )
