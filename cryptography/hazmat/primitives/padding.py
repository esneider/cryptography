# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six

from cryptography.hazmat.primitives import interfaces


class PKCS7(object):
    def __init__(self, block_size):
        super(PKCS7, self).__init__()
        if not (0 <= block_size < 256):
            raise ValueError("block_size must be in range(0, 256)")

        if block_size % 8 != 0:
            raise ValueError("block_size must be a multiple of 8")

        self.block_size = block_size

    def padder(self):
        return _PKCS7PaddingContext(self.block_size)

    def unpadder(self):
        return _PKCS7UnpaddingContext(self.block_size)


@interfaces.register(interfaces.PaddingContext)
class _PKCS7PaddingContext(object):
    def __init__(self, block_size):
        super(_PKCS7PaddingContext, self).__init__()
        self.block_size = block_size
        # TODO: O(n ** 2) complexity for repeated concatentation, we should use
        # zero-buffer (#193)
        self._buffer = b""

    def update(self, data):
        if self._buffer is None:
            raise ValueError("Context was already finalized")

        if isinstance(data, six.text_type):
            raise TypeError("Unicode-objects must be encoded before padding")

        self._buffer += data

        finished_blocks = len(self._buffer) // (self.block_size // 8)

        result = self._buffer[:finished_blocks * (self.block_size // 8)]
        self._buffer = self._buffer[finished_blocks * (self.block_size // 8):]

        return result

    def finalize(self):
        if self._buffer is None:
            raise ValueError("Context was already finalized")

        pad_size = self.block_size // 8 - len(self._buffer)
        result = self._buffer + six.int2byte(pad_size) * pad_size
        self._buffer = None
        return result


@interfaces.register(interfaces.PaddingContext)
class _PKCS7UnpaddingContext(object):
    def __init__(self, block_size):
        super(_PKCS7UnpaddingContext, self).__init__()
        self.block_size = block_size
        # TODO: O(n ** 2) complexity for repeated concatentation, we should use
        # zero-buffer (#193)
        self._buffer = b""

    def update(self, data):
        if self._buffer is None:
            raise ValueError("Context was already finalized")

        if isinstance(data, six.text_type):
            raise TypeError("Unicode-objects must be encoded before unpadding")

        self._buffer += data

        finished_blocks = max(
            len(self._buffer) // (self.block_size // 8) - 1,
            0
        )

        result = self._buffer[:finished_blocks * (self.block_size // 8)]
        self._buffer = self._buffer[finished_blocks * (self.block_size // 8):]

        return result

    def finalize(self):
        if self._buffer is None:
            raise ValueError("Context was already finalized")

        if not self._buffer:
            raise ValueError("Invalid padding bytes")

        pad_size = six.indexbytes(self._buffer, -1)

        if pad_size > self.block_size // 8:
            raise ValueError("Invalid padding bytes")

        mismatch = 0
        for b in six.iterbytes(self._buffer[-pad_size:]):
            mismatch |= b ^ pad_size

        if mismatch != 0:
            raise ValueError("Invalid padding bytes")

        res = self._buffer[:-pad_size]
        self._buffer = None
        return res