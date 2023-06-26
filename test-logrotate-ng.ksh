#!/bin/ksh

SELF="$(basename "${0}")"
LSRC="$(readlink -e "$(which ${0})")"
LSELF="$(basename "${LSRC}")"
DSELF="$(dirname "${LSRC}")"

fatal(){
  echo "${@}" 1>&2
  case $- in *i*) return ${RC:-1};; *) exit ${RC:-1}; esac
}

function seq2 {
  [ $# -gt 1 ] || fatal "[ PAD=width ] seq2 number number [ step ]" || return $?
  typeset m n o; [ $1 -gt $2 ] && o='>' && m=-; for((n=$1; $n ${o:-<}= $2; n=n${m:-+}${3:-1})) { printf %0${PAD:-$(($1 > $2 ? ${#1} : ${#2}))}d'\n' $n; }
}

ext_default=.tar.gz
ext=${EXT}
rotate=${ROTATE:-10}
dir=${DIR:-/dev/shm/1}
conf=${1:-/dev/shm/logrotate-ng.conf}
start=${START}

[ -s ${conf} ] \
  || cat > ${conf} << EOL
${dir} {
   rotate ${rotate}
   recursive
   create
   ${start:+start ${start}}
   ${COMPRESS:+compress${ext:+ ${ext}}}
   ${MAXAGE:+maxage ${MAXAGE}}
   ${MAXSIZE:+maxsize ${MAXSIZE:+$((MAXSIZE-1))}}
   ${HOURLY:+hourly}
   ${DAILY:+daily}
   ${WEEKLY:+weekly}
   ${MONTHLY:+monthly}
   ${YEARLY:+yearly}
}
EOL

sed -Ei '/^\s+$/d' ${conf}
cat ${conf}
[ -n "${HOURLY}${DAILY}${WEEKLY}${MONTHLY}${YEARLY}" ] \
  && when=${HOURLY:+hour}${DAILY:+day}${WEEKLY:+week}${MONTHLY:+month}${YEARLY:+year}
mkdir -p ${dir}
dd if=/dev/zero of=${dir}/a count=${MAXSIZE:-1} bs=1 status=none
[ -n "${HOURLY}${DAILY}${WEEKLY}${MONTHLY}${YEARLY}" ] \
  && touch -d $(date --date="1 ${when} ago" "+%Y-%m-%d %H:%M:%S") ${dir}/a
stat ${dir}/a
du -bs ${dir}/a
case ${ext:-${ext_default}} in
*tar.gz)
  m=z
;;
*tar.bz2)
  m=j
;;
*tar.xz)
  m=J
;;
*)
  fatal "Unsupported compression extension ${ext}"
esac
seq2 $((${rotate}+${start:-1}-1)) ${start:-1} \
| while read s; do
  echo $s > ${dir}/a.${s}
  [ -n "${COMPRESS}" ] \
    && tar --warning=none --remove-files -C ${dir} -c${m}f ${dir}/a.${s}${ext:-${ext_default}} a.${s} 2>/dev/null
  [ -n "${HOURLY}${DAILY}${WEEKLY}${MONTHLY}${YEARLY}" ] \
    || sleep 0.4
done
sleep ${MAXAGE:-0}
stat -c "%n %y" ${dir}/*
${PYTHON} ${DSELF}/logrotate-ng.py ${conf}
stat -c "%n %y" ${dir}/*
grep -q '^\s*compress' ${conf} \
  && find ${dir} -name '*'${ext:-${ext_default}} \
  | while read f; do
    tar --full-time -tvf ${f}
    file ${f}
  done
