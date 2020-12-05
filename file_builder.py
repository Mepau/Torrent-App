from bitarray import bitarray


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
        self.pieces_amount = len(pieces_hash) // 20
        self.blocks_set = {}
        self.filename = None
        self.files = None
        self.file_length = None
        self.pieces_length = pieces_length
        self.pieces_hash = [
            pieces_hash[x - 20 : x] for x in range(len(pieces_hash)) if x % 20 == 0
        ]

        # En caso de generar un solo archivo
        if filename and not files:
            self.filename = filename
            self.file_length = file_length
        # En caso de generar multiples archivo
        elif files:
            self.filename = filename
            self.files = files
            self.file_length = False

    def check_4pieces(self):

        for piece, blocks in self.blocks_set.items():
            pass

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

        pass
