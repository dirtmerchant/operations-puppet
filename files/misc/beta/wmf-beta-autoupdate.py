#!/usr/bin/env python
#######################################################################
# WARNING: this file is managed by Puppet
# puppet:///files/misc/beta/wmf-beta-autoupdate.py
#######################################################################

"""
Updates MediaWiki core and extensions on the Beta cluster

MUST be run as the `mwdeploy` user although that is not enforced by the script.
"""

import argparse
import logging
import os.path
import time
import subprocess
import sys

PATH_MWCORE = '/home/wikipedia/common/php-master'
PATH_MWEXT = '/home/wikipedia/common/php-master/extensions'

# Beta cluster instance used to run Parsoid daemon
PARSOID_INSTANCE = 'deployment-parsoid2.pmtpa.wmflabs'


def main():
    """
    Entry point for the script.

    Parse script arguments, initialize the logger withnice colors and trigger
    the updating tasks.

    Returns 0 on success of ALL tasks, 1 otherwise
    """
    # Parse arguments, init logger to use some colors

    options = parse_args()
    logging.basicConfig(level=options.log_level)
    # Color codes http://www.tldp.org/HOWTO/Bash-Prompt-HOWTO/x329.html
    logging.addLevelName(
        logging.DEBUG, "\033[0;37m%s\033[1;m" %
        logging.getLevelName(logging.DEBUG))
    logging.addLevelName(
        logging.INFO, "\033[1;33m%s\033[1;m" %
        logging.getLevelName(logging.INFO))
    logging.addLevelName(
        logging.WARNING, "\033[1;31m%s\033[1;m" %
        logging.getLevelName(logging.WARNING))
    logging.addLevelName(
        logging.ERROR, "\033[1;41m%s\033[1;m" %
        logging.getLevelName(logging.ERROR))

    logger = logging.getLogger('main')

    parsoid_pre = parsoid_head_ts()

    logger.info("Starting updating tasks...")
    exit_codes = [
        pull_mediawiki(),
        pull_extensions(),
        update_extensions(),
        update_l10n(),
    ]

    parsoid_post = parsoid_head_ts()
    logger.debug('Parsoid HEAD timestamps: %s -> %s',
                 parsoid_pre, parsoid_post)
    if parsoid_post != parsoid_pre:
        logger.info("Updating Parsoid npm dependencies")
        exit_codes.append(update_parsoid_deps())
        logger.info("Restarting updated Parsoid code base")
        exit_codes.append(restart_parsoid())
    else:
        logger.debug('Skipping Parsoid restart since code has not changed')

    logger.info("Executions completed %s", exit_codes)

    final_exit = 0
    for code in exit_codes:
        if code is not 0:
            final_exit = 1
            break

    logger.info("Final exit code: %s", final_exit)
    return final_exit


def parse_args():
    """Parse command line arguments using argparse"""

    parser = argparse.ArgumentParser(description=__doc__)

    log_options = parser.add_mutually_exclusive_group()
    log_options.add_argument(
        '--debug', dest='log_level',
        action='store_const', const=logging.DEBUG,
        help='Print out internal processing')
    log_options.add_argument(
        '-v', '--verbose', '--info', dest='log_level',
        action='store_const', const=logging.INFO,
        help='Give a bit more information about what is going on')
    log_options.add_argument(
        '-q', '--quiet', dest='log_level',
        action='store_const', const=logging.WARNING,
        help='Only shows up warning and errors')

    return parser.parse_args()


def git_head_ts(git_dir):
    proc = subprocess.check_output(
        ['git', '--git-dir', git_dir, 'log',
         '--pretty=tformat:%ct', '-1', 'HEAD'])
    return proc.rstrip('\n')


def parsoid_head_ts():
    """Returns timestamp of the HEAD committer date"""
    return git_head_ts(os.path.join(PATH_MWEXT, 'Parsoid/.git'))


def pull_mediawiki():
    """Updates MediaWiki core"""
    return runner(name='mwcore', path=PATH_MWCORE, cmd=['git', 'pull'])


def pull_extensions():
    """Pull MediaWiki extensions repository"""
    return runner(name='mwextpull', path=PATH_MWEXT, cmd=['git', 'pull'])


def update_extensions():
    """Registers and updates MediaWiki extensions submodules"""
    return runner(name='mwext', path=PATH_MWEXT, cmd=[
        'git', 'submodule', 'update', '--init', '--recursive'])


def update_parsoid_deps():
    """Fetch parsoid Javascript dependencies using npm"""
    parsoid_path = os.path.join(PATH_MWEXT, 'Parsoid/js')
    return runner(name='parsoid-deps', path=parsoid_path, cmd=[
        'npm', 'install', '--verbose', '--color', 'always'])


def restart_parsoid():
    """Restart parsoid daemon via ssh"""
    logger = logging.getLogger(__name__)
    logger.info("restarting parsoid on %s", PARSOID_INSTANCE)

    parsoid_restart_cmd = [
        'ssh', PARSOID_INSTANCE,
        'sudo -u root /etc/init.d/parsoid restart']
    logger.info("Executing %s", parsoid_restart_cmd)
    try:
        cmd = subprocess.Popen(args=parsoid_restart_cmd)
    except OSError, exception:
        logger.error(exception)
        return False

    logger.info('Waiting for parsoid to launch...')
    time.sleep(5)
    logger.info('Checking parsoid is running...')

    try:
        cmd = subprocess.Popen([
            'ssh', PARSOID_INSTANCE,
            '/etc/init.d/parsoid', 'status'])
        status_exit_code = cmd.wait()
    except OSError, exception:
        logger.error(exception)
        return False

    return status_exit_code


def update_l10n():
    """Localisation cache update"""
    return runner(name='mw-update-l10n', cmd=['mw-update-l10n'])


def runner(cmd, path=None, name=None):
    """Wrapper around subprocess.Popen with logging output"""
    log_target = name if name else 'runner'
    logger = logging.getLogger(log_target)

    try:
        if path:
            logger.info("cwd: %s", path)
        logger.info("running: %s", ' '.join(cmd))

        cmd = subprocess.Popen(args=cmd, cwd=path)
        exit_code = cmd.wait()
        logger.info("Exit code: %s", exit_code)
    except OSError, exception:
        logger.error(exception)
        return False

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
