"""Example of how to use chunked encoding and compression"""

import struct
import zlib

from flask import Response, request


# Based on webob's Response object
# See: http://flask.pocoo.org/docs/0.11/patterns/streaming/


def _deflate_iter(app_iter, compresslevel=6):
    """Wrapper that deflates the contents returned by the generator"""
    encoder = zlib.compressobj(compresslevel)
    for item in app_iter:
        yield encoder.compress(item)
        yield encoder.flush(zlib.Z_SYNC_FLUSH)
    yield encoder.flush()


def _gzip_iter(app_iter, compresslevel=6):
    """Wrapper that gzips the contents returned by the generator"""
    size = 0
    crc = zlib.crc32("") & 0xffffffffL
    encoder = zlib.compressobj(compresslevel, zlib.DEFLATED, -zlib.MAX_WBITS,
                               zlib.DEF_MEM_LEVEL, 0)
    yield "\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff"  # gzip header
    for item in app_iter:
        size += len(item)
        crc = zlib.crc32(item, crc) & 0xffffffffL
        yield encoder.compress(item)
    yield encoder.flush()
    yield struct.pack("<2L", crc, size & 0xffffffffL)  # checksum and size


def compressed_chunked(generator, tp="deflate"):
    print "tp=", tp
    func = {
        'deflate': _deflate_iter,
        'gzip': _gzip_iter
    }
    if tp in func:
        res = Response(func[tp](generator))
        res.headers['Content-Encoding'] = tp
        res.headers['Vary'] = 'Accept-Encoding'
    else:
        res = Response(generator)
    return res
