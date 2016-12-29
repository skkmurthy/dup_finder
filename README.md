# dup_finder

Use this to remove duplicates when adding to backup. Here's a set of steps you would follow to backup a "dir-to-backup" into "backup-dir" directory:

1. fingerprint the directory you want to backup: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <dir-to-backup>)```
1. check for duplicates in the "dir-to-backup": 
  1. generate report: ```main.py --mode=check-int-dups --no-log <dir-to-backup> (alt: cid <dir-to-backup)```
  1. the list of dups is dumped out to the console.
  1. manually remove duplicates. Removing internal duplicates has not been implemented yet.
  1. fingerprint "dir-to-backup" again to make sure the fingerprints for deleted files is removed: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <dir-to-backup>)```
  1. rerun the whole step to make sure that you have removed all the internal duplicates
1. Compare against backup directory and remove duplicates from dir-to-backup: 
  1. first detect duplicates: ```main.py --mode=remove-dups <dir-to-backup> <backup-dir> (alt: rd <dir-to-backup> <backup-dir>```
  1. all the detected dups will be in .dp/dups/ folder. Use this command to list all the "dups" directories: ```find <dir-to-backup> -name dups -type d```
  1. Investigate "dups" folders and make sure the files to be deleted are in fact duplicates.
  1. Remove dups folders: ```rm -rf .dup/dups```
1. Move "dir-to-backup" into "backup"
1. Repeat step 2. in "backup-dir" to confirm that no dups were added.

