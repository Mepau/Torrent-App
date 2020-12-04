from constants import THIS_CLIENT_ID
import socket
from bitarray import bitarray


def parse_handshake(str_hshake):

    if str_hshake != 49 + len("BitTorrent protocol"):

        pstrlen = str_hshake[0]
        pstr = str_hshake[1:20]
        reserved = str_hshake[20:28]
        peer_hinfo = str_hshake[28:48]
        peer_id = str_hshake[48:68]

        return peer_hinfo, peer_id

    return False


def do_handshake(info_hash, peer_client, peer_id, bitfield):

    try:
        peer_client.sendall(
            b"%bBitTorrent protocol%b%b"
            % (
                (19).to_bytes(1, byteorder="big"),
                (00000000).to_bytes(8, byteorder="big"),
                info_hash,
            )
        )
        _, found_id = parse_handshake(peer_client.recv(68))
        if found_id:
            if found_id == peer_id:
                peer_client.sendall(THIS_CLIENT_ID.encode())
                if bitfield.count() > 0:
                    peer_client.sendall(
                        b"".join(
                            [
                                (1 + len(bitfield.tobytes())).to_bytes(
                                    4, byteorder="big"
                                ),
                                (5).to_bytes(1, byteorder="big"),
                                bitfield.tobytes(),
                            ]
                        )
                    )
                return True

        return False
    except socket.error as err:
        print(err)
        return False


def recv_handshake(info_hash, peer_client, bitfield):
    try:
        found_ihash, _ = parse_handshake(peer_client.recv(68))

        if found_ihash == info_hash:
            peer_client.sendall(
                b"%bBitTorrent protocol%b%b%b"
                % (
                    (19).to_bytes(1, byteorder="big"),
                    (00000000).to_bytes(8, byteorder="big"),
                    info_hash,
                    THIS_CLIENT_ID.encode(),
                )
            )

            peer_id = peer_client.recv(20)
            if bitfield.count() > 0:
                peer_client.sendall(
                    b"".join(
                        [
                            (1 + len(bitfield.tobytes())).to_bytes(4, byteorder="big"),
                            (5).to_bytes(1, byteorder="big"),
                            bitfield.tobytes(),
                        ]
                    )
                )
            return peer_id.decode()

        return False
    except socket.error as err:
        print(err)
        return False
