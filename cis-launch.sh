#!/bin/bash 

if [[ "$EUID" -ne 0 ]]; then echo -e "\nRun this script with root privileges." ; exit ; fi

log () { logger -t $0 -i "$@" ; echo "$@" ; }

USAGE () {
echo "
Usage: $0 [<options>]
-t	Creates a Text report
-csv	Creates a CSV report
-r	Send results to dir (prompt)
-y	Show all tests
-x	Results XML"
}

fnc_identos () {
## best result is using lsb which requires the redhat-lsb-core package or similar
if [[ -x /usr/bin/lsb_release ]]; then
TMPDISTRO="$( lsb_release -a 2>/dev/null | while read -r line ; do case "$line" in Description*) DISTRO="$(echo ${line#Description*:})" ; break ;; esac ; done )"
case $TMPDISTRO in Red*Hat*6*) DISTRO="RedHat-6" ;; Red*Hat*7*) DISTRO="RedHat-7" ;; Ubuntu*14*) DISTRO="Ubuntu-14" ;; Ubuntu*16*) DISTRO="Ubuntu-16" ;; Ubuntu*18*) DISTRO="Ubuntu-18" ;; Oracle*6*) DISTRO="Oracle-6" ;; Oracle*7*) DISTRO="Oracle-7";; *) echo "Incompatible linux version" ; echo "$TMPDISTRO" ; exit 8 ;; esac
elif [[ -f /etc/oracle-release ]]; then
TMPDISTRO="$(cat /etc/oracle-release)"
case $TMPDISTRO in Oracle*6*) DISTRO="Oracle-6" ;; Oracle*7*) DISTRO="Oracle-7";; *) echo "Incompatible linux version" ; echo "$TMPDISTRO" ; exit 8 ;; esac
elif [[ -f /etc/redhat-release ]]; then
TMPDISTRO="$(\cat /etc/redhat-release)"
case $TMPDISTRO in CentOS*6.*) DISTRO="CentOS-6" ;; CentOS*7.*) DISTRO="CentOS-7" ;; Red*Hat*6.*) DISTRO="RedHat-6" ;; Red*Hat*7.*) DISTRO="RedHat-7" ;; *) echo "Incompatible linux version" ; echo "$TMPDISTRO" ; exit 8 ;; esac
else
TMPDISTRO="$(\uname -r)"
case $TMPDISTRO in *el6*) DISTRO="RedHat-6" ;; *el7*) DISTRO="RedHat-7" ;; *uek6*) DISTRO="Oracle-6" ;; *uek7*) DISTRO="Oracle-7" ;; *generic*) DISTRO="Ubuntu-14" ;; *) echo "Incompatible linux version" ; echo "$TMPDISTRO" ; exit 8 ;; esac
fi 

if [[ ! -n $DISTRO ]]; then echo -e "\tError \$DISTRO has no value, aborting..." ; exit 9 ; fi
unset TMPDISTRO
} ## end fnc_identos

READ=""
RESULT_Pos=""
RESULT_Neg=""
EXIT_Pos=""
EXIT_Neg=""
CONFIRM () {
while true ; do
read -p " 
		${READ} (y/n) "
ANS="$REPLY"
case $ANS in
y|Y|yes|Yes)
${RESULT_Pos}
break
;;
n|N|no|No)
${RESULT_Neg}
${EXIT}
break
;; *) ;; esac ; done
}

declare -a opt_list

GETOPTS () {
case "$OPTS" in
-t|--text) opt_list+=(-t) ;;
-csv|--csv) opt_list+=(-csv) ;;
-r)
LOCATION=""
echo "-r"
until [[ -n "${LOCATION}" && -d "${LOCATION}" && -w "${LOCATION}" ]]; do
read -p "	Where would you like to save the file? "
if [[ ! -d "${REPLY}" ]]; then
echo "		Directory ${REPLY} doesn't seem to exist."
elif [[ ! -w "${REPLY}" ]]; then
echo "		Directory ${REPLY} doesn't seem to be writable."
elif [[ -n "${REPLY}" ]]; then
case "${REPLY}" in
/etc*|/bin*|/cgroup*|/lib*|/misc*|/net*|/proc*|/sbin*|/var*|/boot*|/dev*|/lib64*|/selinux*|/sys*|/usr*|\/|/home|/home/)
echo "		Not allowed to be saved to "${REPLY}"."
LOCATION="" ;; 
*) if [[ -d "${REPLY}" && -w "${REPLY}" ]]; then
LOCATION="${REPLY}"
opt_list+=(-r "${LOCATION}")
fi
;;
esac
else continue ; fi ; done ;;
-y|--all) opt_list+=(-y) ;;
-x) opt_list+=(-orx) ;;
-h) USAGE ; exit 1 ;;
*) echo -e "\n\t\tUnknown option $OPTS" ;; esac
}

until [[ $# -eq 0 ]]; do
OPTS="$1"
GETOPTS
shift
done

script_dir="$( cd "$( dirname "$(readlink -f "$0")" )" && pwd )"
cislocation="$( echo ${script_dir%/scripts}/cis-cat-full )"
mount_location="$( echo ${script_dir%/scripts} )"
case ${cislocation} in
*/*)
if [[ -d "${cislocation}" ]]; then
	case "${cislocation}" in
		/etc*|/bin*|/cgroup*|/lib*|/misc*|/net*|/proc*|/sbin*|/var*|/boot*|/dev*|/lib64*|/selinux*|/sys*|/usr*|\/)
		log "Should not be mounted to "${mount_location}""
		isodir=""
		exit 2
		;;
		.*)
		echo "		Need full, absolute path. Script error."
		exit 2
		;;
	esac 
		if [[ -e ${cislocation}/CIS-CAT.sh ]]; then
		export cislocation
		echo "	Using variable \$cislocation set as "${cislocation}" to access files."
		else
		echo "		${mount_location} invalid location."
		exit 2
		fi
else
	echo "		${cislocation} does not appear to be a valid directory."
	exit 2
fi
;;
" ")
if [[ -n ${cislocation} ]]; then
echo "		Empty directory provided."
exit 2
fi
;; *) if [[ -n ${cislocation} ]]; then echo "		Unrecognized response..." ; exit 2 ; fi ;; esac

log "	Exporting PATH as \$PATH:${mount_location}/java/bin"
export PATH=$PATH:${mount_location}/java/bin
echo -e "\n\tMoving to ${cislocation}"
cd ${cislocation}

fnc_identos

DISTROTST=""
case "$DISTRO" in
CentOS-6) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_CentOS_Linux_6_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
CentOS-7) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_CentOS_Linux_7_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
RedHat-6) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Red_Hat_Enterprise_Linux_6_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
RedHat-7) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Red_Hat_Enterprise_Linux_7_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
Ubuntu-14) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Ubuntu_Linux_14.04_LTS_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
Ubuntu-16) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Ubuntu_Linux_16.04_LTS_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
Ubuntu-18) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Ubuntu_Linux_18.04_LTS_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
Oracle-6) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Oracle_Linux_6_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
Oracle-7) TMPDISTROTST="$(find "${cislocation}/benchmarks" -name CIS_Oracle_Linux_7_Benchmark_v*-xccdf.xml)" ; DISTROTST="."${TMPDISTROTST#${cislocation}}"" ;;
esac

if [[ ${#opt_list[@]} -gt 0 ]]; then
log "
./CIS-CAT.sh -b $DISTROTST -a $(\echo ${opt_list[@]}) "
READ="CIS will run $(\echo ${opt_list[@]}) in addition to a 
		selection of options as seen above.
		Continue?"
RESULT_Pos="./CIS-CAT.sh -b $DISTROTST -a $(\echo ${opt_list[@]}) 2>&1"
RESULT_Neg='echo "Yes master, exiting..."'
EXIT="exit 6"
CONFIRM
else
USAGE
log "
./CIS-CAT.sh -b $DISTROTST -a"
READ="Since no options were provided, 
		this will run a default 
		selection of options as seen above.
		Continue?"
RESULT_Pos="./CIS-CAT.sh -b $DISTROTST -a"
RESULT_Neg='echo "Yes master, exiting..."'
EXIT="exit 7"
CONFIRM
fi

if [[ $? = 0 ]]; then
exit 0
else
log "There seems to have been a problem"
exit 8
fi
