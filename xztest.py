
import subprocess
import tarfile
import os
import sys
import shutil
import json
import time
import zipfile


def rm_rf(path):
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except NotADirectoryError:
        os.unlink(path)

def compress_bz2(archive, directory):
    subprocess.check_call(['tar', 'cfj', archive, directory],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_xz(archive, directory):
    subprocess.check_call(['tar', 'cfJ', archive, directory],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_xz9(archive, directory):
    subprocess.check_call('tar c {} | xz -9 - > {}'
                          .format(directory, archive), shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_gz(archive, directory):
    subprocess.check_call(['tar', 'cfz', archive, directory],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_zopfli(archive, directory, args):
    temp = archive + '.temp'
    try:
        subprocess.check_call('tar cf {} {}'
                              .format(temp, directory), shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call('zopfli/zopfli {} -c {} > {}'
                              .format(temp, args, archive), shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        rm_rf(temp)

def compress_zopfli_default(archive, directory):
    return compress_zopfli(archive, directory, '')

def compress_zopfli_50(archive, directory):
    return compress_zopfli(archive, directory, '--i50')

def compress_zopfli_1000(archive, directory):
    return compress_zopfli(archive, directory, '--i1000')

def compress_7z(archive, directory):
    subprocess.check_call(['7zr', 'a', archive, directory],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_7z9(archive, directory):
    subprocess.check_call(['7zr', 'a', '-mx=9', archive, directory],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_zstd(archive, directory, args):
    temp = archive + '.temp'
    try:
        subprocess.check_call('tar cf {} {}'
                              .format(temp, directory), shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call('zstd/zstd {} {} -o {}'
                              .format(args, temp, archive), shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        rm_rf(temp)

def compress_zstd_default(archive, directory):
    return compress_zstd(archive, directory, '')

def compress_zstd19(archive, directory):
    return compress_zstd(archive, directory, '-19')

def compress_zip(archive, directory):
    shutil.make_archive(archive, 'zip', directory)
    os.rename(archive + '.zip', archive)

def compress_brotli(archive, directory):
    subprocess.check_call('tar c {} | brotli/bin/bro --output {}'
                          .format(directory, archive), shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_brotli24(archive, directory):
    subprocess.check_call('tar c {} | brotli/bin/bro -q 11 -w 24 --output {}'
                          .format(directory, archive), shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def decompress_bz2(archive, directory):
    with tarfile.open(archive, 'r:bz2') as f:
        f.extractall(directory)

def decompress_gz(archive, directory):
    with tarfile.open(archive, 'r:gz') as f:
        f.extractall(directory)

def decompress_xz(archive, directory):
    with tarfile.open(archive, 'r:xz') as f:
        f.extractall(directory)

def decompress_7z(archive, directory):
    subprocess.check_call(['7zr', '-o{}'.format(directory), 'x', archive],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def decompress_zstd(archive, directory):
    temp = archive + '.temp'
    try:
        subprocess.check_call('zstd/zstd -d {} -o {}'.format(archive, temp),
                              shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        os.makedirs(directory, exist_ok=True)
        subprocess.check_call('tar xf {} -C {}'
                              .format(temp, directory), shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        rm_rf(temp)

def decompress_zip(archive, directory):
    with zipfile.ZipFile(archive, 'r') as f:
        f.extractall(directory)

def decompress_brotli(archive, directory):
        os.makedirs(directory, exist_ok=True)
        subprocess.check_call('brotli/bin/bro --decompress --input {} | tar x -C {}'.format(archive, directory),
                              shell=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

COMPRESSORS = {
    'bz2': (compress_bz2, decompress_bz2),
    'gz': (compress_gz, decompress_gz),
    'zopfli': (compress_zopfli_default, decompress_gz),
    'zopfli50': (compress_zopfli_50, decompress_gz),
    # This takes *ages* for minimal gain:
#    'zopfli1000': (compress_zopfli_1000, decompress_gz),
    'xz': (compress_xz, decompress_xz),
    'xz9': (compress_xz9, decompress_xz),
    '7z': (compress_7z, decompress_7z),
    '7z9': (compress_7z9, decompress_7z),
    'zstd': (compress_zstd_default, decompress_zstd),
    'zstd19': (compress_zstd19, decompress_zstd),
    'zip': (compress_zip, decompress_zip),
    'brotli': (compress_brotli, decompress_brotli),
    'brotli24': (compress_brotli24, decompress_brotli),
}


class Timing:
    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, type, value, tb):
        self._end = time.monotonic()

    @property
    def delta(self):
        return self._end - self._start


_this_dir = os.path.dirname(os.path.abspath(__file__))


def get_size_recursive(path):
    dirs = []
    total_size = 0
    for entry in os.scandir(path):
        if entry.is_dir() and not entry.is_symlink():
            dirs.append(entry.path)
        else:
            sr = entry.stat()
            total_size += sr.st_size

    for dir in dirs:
        total_size += get_size_recursive(dir)

    return total_size

def main(filename):
    """Given a conda package, test compress and decompress ratios and times."""
    if not filename.endswith('.tar.bz2'):
        raise ValueError('{} is not a conda package'.format(filename))

    package_name = os.path.basename(filename)[:-8]
    print('Processing {}...'.format(package_name))

    work_dir = os.path.join(_this_dir, 'work', package_name)
    os.makedirs(work_dir, exist_ok=True)

    result_file = os.path.join(work_dir, 'result.json')
    try:
        with open(result_file, 'r') as f:
            result = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        result = {}

    def write_result(result):
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)

    # Step 1: uncompress the tarball and record uncompressed size
    uncompressed_dir = os.path.join(work_dir, 'uncompressed')
    if not os.path.exists(uncompressed_dir) or 'uncompressed_size' not in result:
        print('Unpacking...')
        rm_rf(uncompressed_dir)
        decompress_bz2(filename, uncompressed_dir)
        size = get_size_recursive(uncompressed_dir)
        result['uncompressed_size'] = size
        write_result(result)

    # Step 2: compress the package with all compressors and record
    #         compression time and compressed size:
    for name, (compressor, _) in COMPRESSORS.items():
        archive = os.path.join(work_dir, name + '.test')
        if not os.path.exists(archive) or name not in result or 'compressed_size' not in result[name] or 'compression_time' not in result[name]:
            print('Compressing with {}...'.format(name))
            rm_rf(archive)
            with Timing() as t:
                compressor(archive, uncompressed_dir)
            result[name] = {
                'compression_time': t.delta,
                'compressed_size': os.stat(archive).st_size
            }
            write_result(result)

    # Step 3: run all decompressors in differential timing vs. bz2
    _, decompressor_baseline = COMPRESSORS['bz2']
    for name, (_, decompressor) in COMPRESSORS.items():
        archive = os.path.join(work_dir, name + '.test')
        baseline_archive = os.path.join(work_dir, 'bz2.test')
        if name not in result or 'decompression_time' not in result[name]:
            print('Decompressing with {}...'.format(name))
            decomp_path = os.path.join(work_dir, name + '.decompressed')
            rm_rf(decomp_path)
            times = []
            baseline = []

            N_RUNS = 10
            for x in range(N_RUNS):
                print('Baseline {}%...'.format(x / N_RUNS * 100))
                with Timing() as t:
                    decompressor_baseline(baseline_archive, decomp_path)
                baseline.append(t.delta)
                rm_rf(decomp_path)

            for x in range(N_RUNS):
                print('{} {}%...'.format(name, x / N_RUNS * 100))
                with Timing() as t:
                    decompressor(archive, decomp_path)
                times.append(t.delta)
                rm_rf(decomp_path)

            result[name]['baseline_time'] = baseline
            result[name]['decompression_time'] = times
            write_result(result)

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        main(arg)
