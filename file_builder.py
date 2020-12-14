import hashlib
from bitarray import bitarray
from constants import DEF_BLOCK_LENGTH, DEF_PIECE_LENGTH
from piece_gen import gen_block
import queue
import random
import math


def breq_gen(start_offset: int, end_offset: int, block_length=DEF_BLOCK_LENGTH):
    if end_offset >= start_offset + block_length:
        frac, whole = math.modf((end_offset - start_offset) / block_length)
        if frac:
            lblock_size = int(block_length * frac)
            block_req = [
                (x + start_offset, block_length)
                for x in range(end_offset - start_offset - lblock_size)
                if (x + start_offset) % block_length == 0
                and x + start_offset <= end_offset
            ]
            block_req.append((end_offset + start_offset - lblock_size, lblock_size))
            print(end_offset + start_offset)
            return block_req
        else:
            return [
                (x + start_offset, block_length)
                for x in range(end_offset - start_offset)
                if (x + start_offset) % block_length == 0
                and x + start_offset <= end_offset
            ]


class FileBuilder:
    def __init__(
        self,
        bitfield: bitarray,
        filename,
        file_length: int,
        files,
        pieces_length: int,
        pieces_hash: bytes,
        recv_pieces: dict,
    ):
        self.bitfield = bitfield
        self.pieces_amount = -(-len(pieces_hash) // 20)
        self.file_completed = False
        self.blocks_set = (
            recv_pieces if recv_pieces else {x: [] for x in range(self.pieces_amount)}
        )
        self.filename = None
        self.files = None
        self.file_length = None
        self.pieces_length = pieces_length
        self.pieces_hash = [
            pieces_hash[x : x + 20] for x in range(len(pieces_hash)) if x % 20 == 0
        ]
        self.breq_queue = {x: [] for x in range(self.pieces_amount)}
        self.fst_time = True

        # En caso de generar un solo archivo
        if filename and not files:
            self.filename = filename
            self.file_length = file_length
        # En caso de generar multiples archivo
        elif files:
            self.filename = filename
            self.files = files
            self.file_length = False

        print(
            f"Construyendo archivo {self.filename}, tamaño:{self.file_length}, tamaño de piezas: {self.pieces_length}, cantidad de piezas {self.pieces_amount}"
        )

    def missing_blocks(self, piece_index):

        query = []
        curr_list = self.blocks_set.get(piece_index)

        if curr_list:
            # Explorar el set de piezas para descubrir todos los bloques recibidos
            for x in range(len(curr_list)):
                # Revision para el ultimo bloque

                if x < len(curr_list) - 1:
                    x1_start = curr_list[x].get("block_start")
                    x1_length = curr_list[x].get("length")
                    if curr_list[x + 1]:
                        x2_start = curr_list[x + 1].get("block_start")
                        if x1_start + x1_length == x2_start:
                            pass
                        else:
                            print(f"x1_start: {x1_start} x2_start: {x2_start}")
                            query.append((x1_start, x2_start))
                    else:
                        query.append((x1_start + x1_length, self.pieces_length))

                elif x == len(curr_list) - 1:
                    if piece_index < self.pieces_amount - 1:
                        x1_start = curr_list[x].get("block_start")
                        x1_length = curr_list[x].get("length")
                        if x1_start + x1_length == self.pieces_length:
                            pass
                        else:
                            query.append((x1_start + x1_length, self.pieces_length))
                    elif piece_index == self.pieces_amount - 1:
                        # Revisar para caso de un solo archivo
                        if self.file_length and not self.files:
                            lpiece_frac, lpiece_whole = math.modf(
                                self.file_length / self.pieces_length
                            )

                            fblockq_start = curr_list[x].get("block_start")
                            fblockq_length = curr_list[x].get("length")

                            if lpiece_frac:
                                lpiece_size = int(lpiece_frac * self.pieces_length)
                                if fblockq_start + fblockq_length == lpiece_size:
                                    pass
                                else:
                                    query.append(
                                        (fblockq_start + fblockq_length, lpiece_size)
                                    )
                            else:
                                if fblockq_start + fblockq_length == self.pieces_length:
                                    pass
                                elif (
                                    fblockq_start + fblockq_length < self.pieces_length
                                ):
                                    query.append(
                                        (
                                            fblockq_start + fblockq_length,
                                            self.pieces_length,
                                        )
                                    )
                        # Caso de multiples archivos
                        else:
                            pass
        # No hay bloques en la respectiva pieza
        else:
            if piece_index != self.pieces_amount - 1:
                query.append((0, self.pieces_length))
            # Caso de realizar un query a la ultima pieza
            elif piece_index == self.pieces_amount - 1:
                if self.file_length and not self.files:
                    lpiece_frac, lpiece_whole = math.modf(
                        self.file_length / self.pieces_length
                    )

                    if lpiece_frac:
                        lpiece_size = int(lpiece_frac * self.pieces_length)
                        query.append((0, lpiece_size))
                        print(f"Agregando req de ultima pieza {(0, lpiece_size)}")
                    else:
                        query.append((0, self.pieces_length))
                # Caso para crear req para piezas de multiples archivos
                else:
                    pass
        return query

    def secured_piece(self, piece_index):

        length_counter = 0
        piece = b""
        stored_hash = self.pieces_hash[piece_index]
        piece_hash = None

        for block in self.blocks_set[piece_index]:
            length_counter += block["length"] if block.get("length") else 0
            if self.filename and not self.files:
                piece = b"".join([piece, block["block"]])
                # print(len(piece), block["block_start"], block["length"])
                if piece_index < self.pieces_amount - 1:

                    piece_hash = hashlib.sha1(piece).digest()
                    if piece_hash == stored_hash:
                        print("ESTA FUNCIONANDO")
                        return True
                    elif length_counter >= self.pieces_length:
                        print("clear")
                        self.blocks_set[piece_index].clear()
                        break

                elif piece_index == self.pieces_amount - 1:
                    piece_hash = hashlib.sha1(piece).digest()
                    lpiece_frac, lpiece_whole = math.modf(
                        self.file_length / self.pieces_length
                    )

                    if (
                        length_counter == lpiece_frac * self.pieces_length
                        and piece_hash == stored_hash
                    ):
                        return True
                    elif length_counter >= lpiece_frac * self.pieces_length:
                        self.blocks_set[piece_index].clear()
                        break
        return False

    def make_file(self):
        print("DOWNLOAD COMPLETE.\nBUILDING FILE.")
        with open(f"./downloaded/{self.filename}", "wb") as dl_file:
            for piece_index, blocks in self.blocks_set.items():
                for block in blocks:
                    dl_file.write(block["block"])

    def check_4pieces(self):

        for piece_index, blocks in self.blocks_set.items():
            # Pedidos para respectiva pieza no seran generados si todavia hay pedidos pendientes en su cola
            # Lo mismo si se ha modifica el bit de la pieza debido a que ya se ha obtenido
            if self.blocks_set[piece_index] and not self.bitfield[piece_index]:
                self.blocks_set[piece_index] = sorted(
                    self.blocks_set[piece_index], key=lambda i: i["block_start"]
                )
                if self.secured_piece(piece_index):
                    print("secure piece")
                    self.bitfield[piece_index] = True
            elif (
                len(self.breq_queue[piece_index]) == 0
                and not self.bitfield[piece_index]
            ):

                self.blocks_set[piece_index] = sorted(
                    self.blocks_set[piece_index], key=lambda i: i["block_start"]
                )
                missing_blocks = self.missing_blocks(piece_index)
                print(
                    f"Agregando bloques faltantes: {missing_blocks} de pieza #{piece_index}"
                )
                if missing_blocks:
                    print("Fetching Requests")
                    for start, end in missing_blocks:
                        missed_reqs = breq_gen(start, end)
                        if missed_reqs:
                            random.shuffle(missed_reqs)
                            for offset, block_length in missed_reqs:
                                self.breq_queue[piece_index].append(
                                    (offset, block_length)
                                )
            
        if not self.file_completed:
            if self.bitfield.count(True) == self.pieces_amount:
                self.make_file()
                self.file_completed = True
        

    def insert_block(self, piece_index: int, block_index: int, block: bytes):

        new_block = {"block_start": block_index, "block": block, "length": len(block)}

        if new_block not in self.blocks_set[piece_index]:
            self.blocks_set[piece_index].append(new_block)
            print(f"BLOQUE AGREGADO {(piece_index, block_index, len(block))}")
            if (block_index, len(block)) in self.breq_queue[piece_index]:
                self.breq_queue[piece_index].remove((block_index, len(block)))

    def get_breq(self, piece_index: int):

        if len(self.breq_queue[piece_index]) > 0:
            offset, block_length = self.breq_queue[piece_index].pop(0)
            self.breq_queue[piece_index].append((offset, block_length))
            return offset, block_length
        else:
            return None, None

    def get_block(self, piece_index, start_offset, block_length):

        piece_blocks = self.blocks_set.get(piece_index)
        if piece_blocks:
            found_block = next(
                (
                    block
                    for block in piece_blocks
                    if block["block_start"] == start_offset
                ),
                None,
            )
            if found_block:
                if found_block["length"] == block_length:
                    print(f"found {piece_index, start_offset, block_length}")
                    return found_block["block"]
                else:
                    print(f"not found length {piece_index, start_offset, block_length}")
            else:
                print(f"not found block{piece_index, start_offset, block_length}")
