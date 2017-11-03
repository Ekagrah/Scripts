#!/bin/bash 
if [[ "$EUID" -ne 0 ]]; then echo -e "\t\tRun this script with root privileges." ; exit; fi
script_dir="$( cd "$( dirname "$(readlink -f "$0")" )" && pwd )"
cislocation=`echo ${script_dir%/scripts}/cis-cat-full`
case ${cislocation} in
*/*) if [[ -d "${cislocation}" ]]; then case "${cislocation}" in /etc*|/bin*|/cgroup*|/lib*|/misc*|/net*|/proc*|/sbin*|/var*|/boot*|/dev*|/lib64*|/selinux*|/sys*|/usr*|\/) echo "		Should not be mounted to "${cislocation}"." ; isodir="" ; exit 2 ;; .*) echo "	Need full, absolute path. Script error." ; exit 2 ;; esac ; if [[ -e ${cislocation}/CIS-CAT.sh ]]; then export cislocation ; echo "	Using variable \$isodir set as "${isodir}" to access files." ; else echo "	${cislocation} invalid location." ; exit 2 ; fi ; else echo "	${cislocation} does not appear to be a valid directory." ; exit 2 ; fi ;; " ") if [[ -n ${cislocation} ]]; then echo "		Empty directory provided." ; exit 2 ; fi ;; *) if [[ -n ${cislocation} ]]; then echo "		Unrecognized response..." ; exit 2 ; fi ;; esac
echo "	Exporting PATH as $PATH:${cislocation}/java/bin" && export PATH=$PATH:${cislocation}/java/bin
echo -e "\n\tMoving to ${cislocation}" && cd ${cislocation}
echo -e "\n./CIS-CAT.sh -a -y -orx -f"
while true ; do
read -p " 
		CIS will run with the default 
		selection of options as seen above.
		Continue? (y/n) "
ANS="$REPLY"
case $ANS in y|Y|yes|Yes) ./CIS-CAT.sh -a -y -orx -f 2>&1 ; break ;; n|N|no|No) echo "Exiting..." ; exit 2 ; break ;; *) ;; esac
done
if [[ $? = 0 ]]; then exit 0 ; else echo "There seems to have been a problem." ; exit 5 ; fi
