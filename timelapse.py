#!/usr/bin/env python

#import sys
#sys.exit()

import argparse
import cStringIO
import datetime
import daemonize
import os
import picamera
import socket
import sys
import time

WORKING_DIR = os.path.dirname(os.path.abspath(__file__))


def acquire_lock(lock):
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + lock)
    except socket.error:
        print 'Timelapse script "{0}" is already running'.format(lock)
        sys.exit()


def main(args):
    # Ensure that the timelapse script isn't already running
    acquire_lock(args.app)

    os.chdir(WORKING_DIR)

    # Display some debug info
    print 'Raspberry Pi Timelapse'
    print '\n'.join('{0}: {1}'.format(k, v) for k, v in args._get_kwargs())

    # Initialize the camera
    camera = picamera.PiCamera()
    camera.start_preview()
    time.sleep(2)  # Give the camera time to initialize
    stream = cStringIO.StringIO()

    # Timelapse!
    try:
        for io in camera.capture_continuous(stream, format='jpeg'):
            now = datetime.datetime.now()
            counter = len(os.listdir(os.path.dirname(args.output)))
            filename = args.output.format(counter=counter, timestamp=now)
            filename = os.path.join(WORKING_DIR, filename)

            img = open(filename, 'wb')
            img.write(io.getvalue())
            img.close()

            print '{0}: {1}'.format(now, filename)

            # Reset the string and sleep
            io.seek(0)
            io.truncate()
            time.sleep(args.interval)
    except Exception:
        camera.stop_preview()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interval', type=int, default=30,
        help='how often to snap a picture (in seconds)')
    parser.add_argument('-o', '--output', default='snapshots/timelapse-{counter:06d}.jpg',
        help='what each image should be saved as')
    parser.add_argument('-a', '--app', default='timelapse',
        help='app name, used for process lock and daemonize')
    parser.add_argument('-d', '--daemonize', default=False, action='store_true',
        help='daemonize the process')
    parser.add_argument('-p', '--pid', default='/tmp/timelapse.pid',
        help='location to write the pid file')

    args = parser.parse_args()

    if args.daemonize:
        print 'Daemonizing...'
        daemon = daemonize.Daemonize(app=args.app, pid=args.pid, action=main)
        daemon.start()
    else:
        try:
            main(args)
        except KeyboardInterrupt:
            print 'Quitting...'
        except Exception, err:
            print '[err] {0}: {1}'.format(err.__class__.__name__, err)
