@echo off
powercfg /h off >NUL 2>&1
powercfg /S 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >NUL 2>&1
fsutil behavior set disable8dot3 1 >NUL 2>&1
fsutil behavior set disablecompression 1 >NUL 2>&1
fsutil behavior set disableEncryption 1 >NUL 2>&1
fsutil behavior set disableLastAccess 1 >NUL 2>&1
