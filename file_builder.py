from bitarray import bitarray
from functools import reduce
from constants import DEF_BLOCK_LENGTH, DEF_PIECE_LENGTH
import math
import queue
import random


class FileBuilder:
    def __init__(
        self,
        bitfield: bitarray,
        filename,
        file_length,
        files,
        pieces_length,
        pieces_hash: bytes,
    ):
        self.bitfield = bitfield
        self.pieces_amount = -(-len(pieces_hash) // 20)
        self.blocks_set = {x: [] for x in range(self.pieces_amount)}
        self.filename = None
        self.files = None
        self.file_length = None
        self.pieces_length = pieces_length
        self.pieces_hash = [
            pieces_hash[x : x + 20] for x in range(len(pieces_hash)) if x % 20 == 0
        ]
        self.breq_queue = {x: queue.Queue() for x in range(self.pieces_amount)}

        # En caso de generar un solo archivo
        if filename and not files:
            self.filename = filename
            self.file_length = file_length
        # En caso de generar multiples archivo
        elif files:
            self.filename = filename
            self.files = files
            self.file_length = False

    def query_blocks(self, piece_index):

        query = []
        for x in range(len(self.blocks_set.get(piece_index))):
            if x != len(self.blocks_set.get(piece_index)) - 1:
                x1_start = self.blocks_set.get(piece_index)[x].get("block_start")
                x1_length = self.blocks_set.get(piece_index)[x].get("length")
                x2_start = self.blocks_set.get(piece_index)[x + 1].get("block_start")
                if x1_start + x1_length == x2_start:
                    query.append((x1_start, x1_length, x2_start, True))
                else:
                    query.append((x1_start, x1_length, x2_start, False))
            else:
                fpiece_start = self.blocks_set.get(piece_index)[x].get("block_start")
                fpiece_length = self.blocks_set.get(piece_index)[x].get("length")
                last_offset = fpiece_start + fpiece_length
                query.append((fpiece_start, fpiece_length, last_offset))

    def look_4blocks(self, query_list, block_length=DEF_BLOCK_LENGTH):

        desired_blocks = []
        for x in range(len(query_list)):
            if x != len(query_list) - 1:
                if query_list[x][3]:
                    pass
                else:
                    next_offset = query_list[x][0] + query_list[x][1]
                    if next_offset + block_length <= query_list[x][2]:
                        nextb_length = block_length
                        desired_blocks.append((next_offset, nextb_length))
                    else:
                        nextb_length = query_list[x][2] - next_offset
                        desired_blocks.append((next_offset, nextb_length))
            else:
                pass

    def block_rgen(
        self, piece_index, piece_length=DEF_PIECE_LENGTH, block_length=DEF_BLOCK_LENGTH
    ):

        # En caso de generar pedidos de bloques para un solo archivo
        if self.file_length:

            # Generar pedidos de bloques para piezas que no sean la ultima
            if piece_index < self.pieces_amount - 1:
                return [
                    (x, x + block_length)
                    for x in range(piece_length)
                    if x % block_length == 0
                ]
            # Generar pedidos de bloques para la ultima pieza
            elif piece_index == self.pieces_amount - 1:
                piece_frac, piece_whole = math.modf(self.file_length / piece_length)
                lpiece_size = piece_length * piece_frac
                # En caso de que la ultima pieza no sea del mismo tamaño que las otras
                if piece_frac:
                    block_frac, block_whole = math.modf(lpiece_size / block_length)
                    # En caso de que el ultimo bloque no sea del mismo tamaño que los otros
                    if block_frac:
                        lblock_size = block_length * block_frac
                        block_req = [
                            (x, x + block_length)
                            for x in range(int(lpiece_size - lblock_size))
                            if x % block_length == 0
                        ]
                        block_req.append(
                            (int(lpiece_size - lblock_size), int(lpiece_size))
                        )
                        return block_req
                    else:
                        return [
                            (x, x + block_length)
                            for x in range(lpiece_size)
                            if x % block_length == 0
                        ]
                else:
                    return [
                        (x, x + block_length)
                        for x in range(piece_length)
                        if x % block_length == 0
                    ]

    def check_4pieces(self):

        for piece_index, blocks in self.blocks_set.items():

            # Pedidos para respectiva pieza no seran generados si todavia hay pedidos pendientes en su cola
            # Lo mismo si se ha modifica el bit de la pieza debido a que ya se ha obtenido
            if (
                not self.bitfield[piece_index]
                and self.breq_queue[piece_index].qsize() == 0
            ):
                if self.blocks_set[piece_index]:
                    self.blocks_set[piece_index] = sorted(
                        blocks, key=lambda i: i["block_start"]
                    )
                else:
                    desired_blocks = self.block_rgen(piece_index)
                    random.shuffle(desired_blocks)
                    for offset, block_length in desired_blocks:
                        self.breq_queue[piece_index].put(
                            (piece_index, offset, block_length)
                        )

    def insert_block(self, piece_index: int, block_index, block: bytes):
        try:
            self.blocks_set[piece_index].append(
                {"block_start": block_index, "block": block, "length": len(block)}
            )
        except KeyError:
            self.blocks_set[piece_index] = []
            self.blocks_set[piece_index].append(
                {"block_start": block_index, "block": block, "length": len(block)}
            )
