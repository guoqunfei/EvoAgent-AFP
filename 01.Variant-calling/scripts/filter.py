#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import sys
import gzip

def main():

    line_number = 0
    with gzip.open(sys.argv[1], 'rt') as f_in:
        for line in f_in:
            line_number += 1


            if line_number % 4 == 1:
                q_value = line.rstrip('\n').split('_')[-1]
                line1 = line.rstrip('\n')
            elif line_number % 4 == 2:
                r_len = len(line.rstrip('\n'))
                line2 = line.rstrip('\n')
            elif line_number % 4 == 3:
                line3 = line.rstrip('\n')
            elif line_number % 4 == 0:
                line4 = line.rstrip('\n')
                if float(q_value) > 7 and int(r_len) > 2000:
                    print('\n'.join([line1, line2, line3, line4]))

if __name__ == "__main__":
    main()
