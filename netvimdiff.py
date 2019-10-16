#!/usr/bin/env python
#
# MIT License
#
# Copyright (c) 2019 David Cachau <safranil@safranil.fr>
# Copyright (c) 2019 CAPSI Informatique
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from __future__ import print_function

import re
import subprocess
import sys
import os
import tempfile
import shutil


def parse_file(file, index):
    remote_match = re.match('^((?:[A-Za-z0-9-_]+@|)[A-Za-z0-9-_.]+):(.+)$', file)
    if remote_match is not None:
        return {'remote': remote_match.group(1), 'file': remote_match.group(2), 'index': index}
    elif file is not None and file != '':
        return {'remote': None, 'file': file, 'index': index}
    else:
        return {'remote': None, 'file': None, 'index': index}


def get_temp_dir():
    return tempfile.mkdtemp(prefix='vimdiff-')


def rsync(file_from, file_to):
    ret_code = -1
    while ret_code != 0:
        ret_code = subprocess.call(['rsync', '--verbose', '--inplace', file_from, file_to])
        if ret_code != 0:
            while True:
                yn = raw_input('The rsync command had failed with code %i, retry (yes/no)? ' % ret_code)
                if yn == 'yes':
                    break
                elif yn == 'no':
                    print('Okay, I will NOT send this file:')
                    print('"%s" to "%s"' % (file_from, file_to))
                    return False
    return True


def download_file(remote, remote_file, local_file):
    print('Downloading %s from %s to temp file %s' % (remote_file, remote, local_file))
    return rsync('%s:%s' % (remote, remote_file), local_file)


def upload_file(local_file, remote, remote_file):
    print('Uploading %s to %s from temp file %s' % (local_file, remote_file, remote))
    return rsync(local_file, '%s:%s' % (remote, remote_file))


if len(sys.argv) == 1:
    print("Usage: %s [[user@]remote-server:]file [[user@]remote-server:]file " % (sys.argv[0]) +
          "[[[user@]remote-server:]file [[[user@]remote-server:]file]]")
    print("")
    print("Edit and compare files from local and remote sources")
    sys.exit(1)

files = []

for i in range(1, 5):
    try:
        f = parse_file(sys.argv[i], i)
        if f['remote'] is None and f['file'] is None:
            print("Arg %i is not valid" % i)
            sys.exit(2)
        files.append(f)
    except IndexError:
        pass

if len(files) < 2:
    print('You had to pass between 2 and 4 files to edit')
    exit(3)

has_error = False
tmp_dir = get_temp_dir()
for file in files:
    if file['remote'] is not None:
        tmp_file = '%s/%i-%s-%s' % (tmp_dir, file['index'], file['remote'], os.path.basename(file['file']))
        success = download_file(file['remote'], file['file'], tmp_file)
        has_error |= not success
        file['temp'] = tmp_file
    else:
        file['temp'] = None

vim_args = ['vimdiff']
for file in files:
    if file['temp'] is not None:
        vim_args.append(file['temp'])
    else:
        vim_args.append(file['file'])

ret_code = subprocess.call(vim_args)

if ret_code != 0:
    while True:
        yn = raw_input('vim has return with the code %i, do you want to send files to remotes (yes/no)? ' % ret_code)
        if yn == 'yes':
            print('Okay, I will send all files for you')
            break
        elif yn == 'no':
            print('Okay, I will NOT send files')
            print('If you want to find files on the local filesystem, you can find them in:')
            print(tmp_dir)
            print('You can edit and send files manually, don\'t forget to delete the temporary directory.')
            sys.exit(4)


for file in files:
    if file['remote'] is not None:
        success = upload_file(file['temp'], file['remote'], file['file'])
        has_error |= not success

if has_error:
    print('The temp dir has not been removed due previous to errors.')
    print('Please remove manually the following directory:')
    print(tmp_dir)
elif tmp_dir != '' and tmp_dir != '/':
    print('Removing temporary directory')
    subprocess.call(["rm", "--preserve-root", "-rf", tmp_dir])
