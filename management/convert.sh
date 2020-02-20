#!/usr/bin/env bash

find . -name '*.gz' -exec gunzip -f {} \;
find . -name '*.zip' -execdir unzip -o {} \; -delete
find . -name '__MACOSX' -type d -delete
find . -name '.DS_STORE' -delete

IFS=$'\n'
for i in $(find . -name '*.geojson' -print); do
	if [ $(cat "${i}" | wc -l) -gt 50 ]; then continue; fi
	echo ${i}
	json_pp < "${i}" > "${i}.new"
	mv "${i}.new" "${i}"
done

for i in $(find . -name '*.osm' -print); do
	OUT="${i%.*}_new.geojson"
	FINAL="${i%.*}.geojson"
	node --max_old_space_size=8192 $(which osmtogeojson) "${i}" > "${OUT}"
	if [ -f "${FINAL}" ]; then
		diff "${OUT}" "${FINAL}" > /dev/null
		if [ $? == 0 ]; then
			mv "${OUT}" "${FINAL}"
		fi
	elif [ ! -f "${FINAL}" ]; then
		mv "${OUT}" "${FINAL}"
	fi
done

find . -mindepth 2 -name '*.sh' -type f -execdir sh "{}" \;
