# dup_finder

## Case 1: Copying files from a RW directory:
Use this to remove duplicates when adding to backup. Here's a set of steps you would follow to backup a "dir-to-backup" into "backup-dir" directory:

1. fingerprint the directory you want to backup: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <dir-to-backup>)```
1. check for duplicates in the "dir-to-backup": 
  1. generate report: ```main.py --mode=check-int-dups --no-log <dir-to-backup> (alt: cid <dir-to-backup>)```
  1. the list of dups is dumped out to the console.
  1. manually remove duplicates. Removing internal duplicates has not been implemented yet.
  1. fingerprint "dir-to-backup" again to make sure the fingerprints for deleted files is removed: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <dir-to-backup>)```
  1. rerun the whole step to make sure that you have removed all the internal duplicates
1. Compare against backup directory and remove duplicates from dir-to-backup: 
  1. first detect duplicates: ```main.py --mode=remove-dups <dir-to-backup> <backup-dir> (alt: rd <dir-to-backup> <backup-dir>```
  1. all the detected dups will be in .dp/dups/ folder. Use this command to list all the "dups" directories: ```find <dir-to-backup> -name dups -type d```
  1. Investigate "dups" folders and make sure the files to be deleted are in fact duplicates.
  1. Remove dups folders: ```rm -rf .dup/dups```
1. Move "dir-to-backup" into "backup-dir"
1. Repeat step 2. in "backup-dir" to confirm that no dups were added.

## Case 2: Copying from RO directory:

For case where the "dir-to-backup" is on a RO mount/directory, the "working directory" cannot be created on "dir-to-backup" and needs to created elsewhere.

Here's the procedure:

1. Add the mount/parent directory in which "dir-to-backup" resides to [rd_only_dirs](rd_only_dirs). dp_work_dir (in the current path) will be used as the "working directory". A mirror image of the directory structure within "dir-to-backup" is created and Log and fingerprint DB files are stored here.
1. fingerprint the directory you want to backup: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <dir-to-backup>)```. Note that Fingerpring DB file and log files for the run will be placed in dp_work_dir.
1. You now need to copy unique files from the read-only directory to a read-write staging directory ("stage-dir"): ```main.py --mode=copy-uniq-files [-v --no-log] <dir-to-backup> <backup-dir> <stage-dir> (alt: cuf <dir-to-backup> <backup-dir> <stage-dir>)```. This command compares files in "dir-to-backup" with files in "backup-dir" and only copies only the files unique to "dir-to-backup" to "stage-dir".
1. check for duplicates in the "stage-dir": 
  1. generate report: ```main.py --mode=check-int-dups --no-log <stage-dir> (alt: cid <stage-dir>)```
  1. the list of dups is dumped out to the console.
  1. manually remove duplicates. Removing internal duplicates has not been implemented yet.
  1. fingerprint "dir-to-backup" again to make sure the fingerprints for deleted files is removed: ```main.py --mode=fingerprint <dir-to-backup> (alt: fp <stage-dir>)```
  1. rerun the whole step to make sure that you have removed all the internal duplicates
1. Move from "stage-dir" into "backup-dir"
1. Repeat step 2. in "backup-dir" to confirm that no dups were added.
