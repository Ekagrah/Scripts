#!/bin/bash


USAGE () {
echo -e "\nUsage: $0 [<sum-type>] [<file>] [<sum-to-match>]\nsumtype includes: md5 sha512 sha256"
}

if [[ $# -ne 3 ]]; then
	USAGE
	exit 1
fi



case "$1" in
	md5|md5sum)
		sumtest="$(md5 ${2})"
		;;
	sha512|shasum512)
		sumtest="$(shasum -a 512 ${2})"
		;;
	sha256|shasum256)
		sumtest="$(shasum -a 256 ${2})"
		;;
	*)
		echo "
		Unknown option $1"
		exit 2
		;;
esac

if [[ "$(echo ${sumtest} | grep -Eo '[[:alnum:]]{21,}')" = "$3" ]] ; then echo -e "\x1B[37;42;1m\n matches \x1B[0m" ; else echo -e "\x1B[93;41;5m\n no match \x1B[0m" ; fi

exit 0
