io-shinken-checks-linux
=======================

Specifics checks for linux based on pure ssh polling, with nothing to install on the target


Dependencies
======================
 * python
 * python-paramiko




Connexion
======================
This check is for checking the SSH connexion to the distant server.

  $ check_ssh_connexion.py -H localhost -u shinken



Memory
======================
The Memory check is done by the check_memory_by_ssh.py script.

  $ check_memory_by_ssh.py -H localhost -u shinken -w "75%" -c "90%"




Uptime
======================
The Uptime check is done by the check_uptime_by_ssh.py script. It only take a -c option, the number of second : below it's critical, higher it's ok. By default it's 3600s.

  $ check_uptime_by_ssh.py -H localhost -u shinken -c 3600



NTP Sync
======================
The NTP sync check is done by the check_ntp_sync_by_ssh.py script. It will go in warning if no ntp server is the reference, and -w/-c options will set the maximum delay values.

  $ check_ntp_sync_by_ssh.py -H localhost -u shinken -w 10 -c 60


Processes (Memory)
=====================
Look at the memory of a process, or a pack of processes. It's done by the check_processes_by_ssh script

  Look that the sum of all *chrome* processes are not over 700 or 800MB
  $check_processes_by_ssh.py -H localhost -u shinken -C chrome -w 700 -c 800 -S

  Look for each *chrome* processe if they are not over 100 or 200MB
  $check_processes_by_ssh.py -H localhost -u shinken -C chrome -w 100 -c 200
  
  Look for all process, and warn if one is over 100/200MB
  $check_processes_by_ssh.py -H localhost -u shinken -w 100 -c 200 


Disks
======================
The Disks check is done by the check_disks_by_ssh.py script.

  $ check_disks_by_ssh.py -H localhost -u shinken -w "75%" -c "90%"



Load average
=====================
The load average values are checks with the check_load_average_by_ssh script.
There are two modes : strict values, and cpu based values. 'default : strict)

  Will warn if the load average is highen than 1 or 2
  $ check_load_average_by_ssh.py -H localhost -u shinken -w 1,1,1 -c 2,2,2

  Will warn if the load average is highen than 1*nb_cpus or 2*nb_cpus
  $ check_load_average_by_ssh.py -H localhost -u shinken -w 1,1,1 -c 2,2,2 -C
  
  
CPU activities
====================
The cpu states are checks by the check_cpu_stats.py script. There is no warning or critical values need here.

  $ check_cpu_stats.py -H localhost -u shinken



DISKS activities
===================
The disks I/O are checked by the check_disks_stats_by_ssh.py. No warning nor critical values need.

  $ check_disks_stats_by_ssh.py -H localhost -u shinken



TCP states
==================
The TCP states are checked by the check_tcp_states_by_ssh.py plugin. No warning nor critical values need.

  $ check_tcp_states_by_ssh.py - H localhost -u shinken


KERNEL stats
==================
The KERNEL states are checked by the check_kernel_stats_by_ssh.py plugin. No warning nor critical values need.

  $ check_kernel_stats_by_ssh.py - H localhost -u shinken


NFS stats
==================
The NFS states are checked by the check_nfs_stats_by_ssh.py plugin. No warning nor critical values need.

  $ check_nfs_stats_by_ssh.py - H localhost -u shinken



Interface activities
=================
The network activity is checked by the check_net_stats_by_ssh.py plugin. No need for warning nor critical.

  $ check_net_stats_by_ssh.py - H localhost -u shinken

Read Only file systems
==================
The file system mount are checks. If a FS is in read only, it will raise a critical error.

  $ check_ro_filesystem_by_ssh.py - H localhost -u shinken

