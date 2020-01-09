#!/usr/bin/env python3

import sys, os
import struct
import argparse

def check_file_magic(f, expected_magic):
	old_offset = f.tell()
	try:
		magic = f.read(len(expected_magic))
	except:
		return False
	finally:
		f.seek(old_offset)
	return magic == expected_magic

class MyParser(argparse.ArgumentParser):
	def error(self, message):
		self.print_help()
		sys.stderr.write('\nerror: {0}\n'.format(message))
		sys.exit(2)

parser = MyParser(description='pak tool')
parser.add_argument('input_file', type=str, help='package file')
parser.add_argument('out_dir_path', type=str, help='output directory')
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show details')

if len(sys.argv) == 1:
	parser.print_usage()
	sys.exit(1)

args = parser.parse_args()

in_file_path = args.input_file
if not os.path.isfile(in_file_path):
	parser.error('invalid input file path: {0}'.format(in_file_path))

out_dir_path = args.out_dir_path
if not os.path.exists(out_dir_path):
	os.makedirs(out_dir_path)
elif not os.path.isdir(out_dir_path):
	parser.error('invalid output directory path: {0}'.format(out_dir_path))

if args.verbose:
	print('loading package file: {0}'.format(in_file_path))

fmt = '>2sIIH'
count = 0
with open(in_file_path, 'rb') as in_f:
	while in_f and check_file_magic(in_f, b'ZH'):
		data = in_f.read(struct.calcsize(fmt))
		if len(data) != struct.calcsize(fmt):
			print('error: insufficient header data')
			sys.exit(1)
		magic, in_size, out_size, name_len = struct.unpack(fmt, data)

		name = in_f.read(name_len)
		if len(name) != name_len:
			print('error: insufficient name data')
			sys.exit(1)
		name = name.decode('utf-8')

		if args.verbose:
			print('processing file: {0}'.format(name))

		data = in_f.read(in_size)
		if len(data) != in_size:
			print('error: insufficient source data')
			sys.exit(1)

		if in_size == out_size:
			# not compressed
			if args.verbose:
				print('  not compressed')
		else:
			# some sort of LZO compression
			if args.verbose:
				print('  compressed')

			buf = bytearray(0x1000)
			buf_pos = 0xFEE

			out_data = bytearray()
			src_pos = dst_pos = 0
			while src_pos < in_size and dst_pos < out_size:
				flag = data[src_pos]
				src_pos += 1

				for i in range(8):
					if flag & (1 << i): # use as is
						buf[buf_pos] = data[src_pos]
						out_data.append(buf[buf_pos])
						src_pos += 1
						dst_pos += 1
						buf_pos = (buf_pos + 1) & 0xFFF
					else:
						lo, hi = data[src_pos], data[src_pos + 1]
						src_pos += 2

						offset = lo | (((hi >> 4) & 0xF) << 8)
						count = (hi & 0xF) + 0x3

						for j in range(count):
							buf[buf_pos] = buf[(offset + j) & 0xFFF]
							out_data.append(buf[buf_pos])
							buf_pos = (buf_pos + 1) & 0xFFF

						dst_pos += count

					if src_pos >= in_size or dst_pos >= out_size:
						break

			if len(out_data) != out_size:
				print('error: insufficient destination data')
				sys.exit(1)

			data = out_data

		out_file_path = os.path.join(out_dir_path, name)
		out_dir_path = os.path.split(out_file_path)[0]
		if not os.path.isdir(out_dir_path):
			os.makedirs(out_dir_path)
		
		with open(out_file_path, 'wb') as out_f:
			out_f.write(data)

		count += 1

if count == 0:
	print('error: invalid package format')
	sys.exit(1)

if args.verbose:
	print('done')
