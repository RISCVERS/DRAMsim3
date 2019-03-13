#! /usr/bin/env python3

import argparse
import os
import random
import uuid


class Generator():
    """
    Format agnostic address stream generator
    """

    def __init__(self, stream_type, interarrival, ratio):
        # convert to 0 ~ 1 for easier random generation
        self._interval = interarrival
        self._ratio = ratio / (ratio + 1.0)

        self._gen = None

        # 4GB range ought to be enough...
        self._range = 2 ** 32
        self._last_clk = 0
        self._last_rd_addr = random.randrange(self._range)
        self._last_wr_addr = random.randrange(self._range)
        if stream_type == 'random':
            self._gen = self._rand_gen
        elif stream_type == 'stream':
            self._gen = self._stream_gen
        else:
            pass

    def _get_op(self):
        if random.random() > self._ratio:
            return 'w'
        else:
            return 'r'

    def _rand_gen(self):
        addr = random.randrange(self._range)
        op = self._get_op()
        return (op, addr)

    def _stream_gen(self):
        op = self._get_op()
        if op == 'r':
            self._last_rd_addr += 64
            return (op, self._last_rd_addr)
        else:
            self._last_wr_addr += 64
            return (op, self._last_wr_addr)

    def gen(self):
        op, addr = self._gen()
        self._last_clk += self._interval
        return (op, addr, self._last_clk)


def get_string(op, addr, clk, trace_format):
    op_map = {
        'r': {
            'dramsim2': 'READ',
            'dramsim3': 'READ',
            'ramulator': 'R',
            'drsim': 'READ'
        },
        'w': {
            'dramsim2': 'WRITE',
            'dramsim3': 'WRITE',
            'ramulator': 'W',
            'drsim': 'WRITE'
        }
    }
    actual_op = op_map[op][trace_format]
    if 'dramsim' in trace_format:
        return '{} {} {}'.format(hex(addr), actual_op, clk)
    elif 'ramulator' == trace_format:
        return '{} {}'.format(hex(addr), actual_op)
    elif 'drsim' == trace_format:
        return '{} {} {} 64B'.format(hex(addr), actual_op, clk)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Trace Generator for Various DRAM Simulators")
    parser.add_argument('-s', '--stream-type', default='random',
                        help='Address stream type, (r)andom, (s)tream, (m)ix')
    parser.add_argument('-i', '--interarrival',
                        help='Inter-arrival time in cycles',
                        type=int, default=10)
    parser.add_argument('-f', '--format', default='all',
                        help='Trace format, dramsim2, dramsim3,'
                        'ramulator, drsim, or all')
    parser.add_argument("-o", "--output-dir",
                        help="output directory", default=".")
    parser.add_argument('-r', '--ratio', type=float, default=2,
                        help='Read to write(1) ratio')
    parser.add_argument('-n', '--num-reqs', type=int, default=100,
                        help='Total number of requests.')

    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        try:
            os.mkdir(args.output_dir)
        except (OSError, ValueError) as e:
            print('Cannot use output path:' + args.output_dir)
            print(e)

    stream_types = {'r': 'random', 'random': 'random',
                    's': 'stream', 'stream': 'stream',
                    'm': 'mix', 'mix': 'mix'}
    stream_type = stream_types.get(args.stream_type, 'random')

    formats = ['dramsim2', 'dramsim3', 'ramulator', 'drsim']
    if args.format != 'all':
        formats = [args.format]

    files = {}
    for f in formats:
        file_name = '{}_{}_i{}_n{}_rw{}.trace'.format(
            f, stream_type, args.interarrival, args.num_reqs, int(args.ratio))
        if f == 'dramsim2':
            file_name = 'mase_' + file_name
        files[f] = os.path.join(args.output_dir, file_name)

    # open files
    for f, name in files.items():
        fp = open(name, 'w')
        files[f] = fp

    g = Generator(stream_type, args.interarrival, args.ratio)
    for i in range(args.num_reqs):
        op, addr, clk = g.gen()
        for f in formats:
            line = get_string(op, addr, clk, f)
            files[f].write(line + '\n')
