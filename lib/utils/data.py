# Copyright 2013-2020 Aerospike, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'aerospike'

lsof_file_type_desc = {
    'GDIR': 'GDIR', 'GREG': 'GREG', 'VDIR': 'VDIR', 'IPv4': 'IPv4 socket', 'IPv6': 'IPv6 network file', 'ax25': 'Linux AX.25 socket',
    'inet': 'Internet domain socket', 'lla': 'HP-UX link level access file', 'rte': 'AF_ROUTE socket', 'sock': 'socket of unknown domain',
    'unix': 'UNIX domain socket', 'x.25': 'HP-UX x.25 socket', 'BLK': 'block special file', 'CHR': 'character special file',
    'DEL': 'Deleted Linux map file', 'DIR': 'directory', 'DOOR': 'VDOOR file', 'FIFO': 'FIFO special file', 'KQUEUE': 'BSD style kernel event queue file',
    'LINK': 'symbolic link file', 'MPB': 'multiplexed block file', 'MPC': 'multiplexed character file', 'NOFD': "Linux /proc/<PID>/fd directory that can't be opened",
    'PAS': "/proc/as file", 'PAXV': "/proc/auxv file", 'PCRE': "/proc/cred file", 'PCTL': "/proc control file", 'PCUR': "current /proc process",
    'PCWD': "/proc current working directory", 'PDIR': "/proc directory", 'PETY': "/proc executable type (etype)", 'PFD': "/proc file descriptor",
    'PFDR': "/proc file descriptor directory", 'PFIL': "executable /proc file", 'PFPR': "/proc FP register set", 'PGD': "/proc/pagedata file", 'PGID': "/proc group notifier file",
    'PIPE': 'pipes', 'PLC': "/proc/lwpctl file", 'PLDR': "/proc/lpw directory", 'PLDT': "/proc/ldt file", 'PLPI': "/proc/lpsinfo file", 'PLST': "/proc/lstatus file",
    'PLU': "/proc/lusage file", 'PLWG': "/proc/gwindows file", 'PLWI': "/proc/lwpsinfo file", 'PLWS': "/proc/lwpstatus file", 'PLWU': "/proc/lwpusage file",
    'PLWX': "/proc/xregs file", 'PMAP': "/proc map file (map)", 'PMEM': "/proc memory image file", 'PNTF': "/proc process notifier file",
    'POBJ': "/proc/object file", 'PODR': "/proc/object directory", 'POLP': "old format /proc light weight process file", 'POPF': "old format /proc PID file",
    'POPG': "old format /proc page data file", 'PORT': "SYSV named pipe", 'PREG': "/proc register file", 'PRMP': "/proc/rmap file", 'PRTD': "/proc root directory",
    'PSGA': "/proc/sigact file", 'PSIN': "/proc/psinfo file", 'PSTA': "/proc status file", 'PSXSEM': "POSIX semaphore file", 'PSXSHM': "POSIX shared memory file",
    'PUSG': "/proc/usage file", 'PW': "/proc/watch file", 'PXMP': "/proc/xmap file", 'REG': "regular file", 'SMT': "shared memory transport file",
    'STSO': "stream socket", 'UNNM': "unnamed type file", 'XNAM': "OpenServer Xenix special file of unknown type", 'XSEM': "OpenServer Xenix semaphore file",
    'XSD': "OpenServer Xenix shared data file"
}
