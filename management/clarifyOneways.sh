#!/usr/bin/env bash
set -ex

mkdir -p clarified

find . -name '*.geojson' -path './clarified/' -prune -o -exec cp {} clarified/ \;

replace=('s/ONE_WAY_SAME_DIRECTION/oneway=yes/g' 's/ONE_WAY_REVERSE_DIRECTION/oneway=-1/g' 's/ONE_WAY_TO_REVERSED_ONE_WAY/oneway=-1/g' 's/ONE_WAY_TO_TWO_WAY/oneway=no/g' 's/TWO_WAY_TO_ONE_WAY/oneway=yes/g' 's/TWO_WAY_TO_REVERSED_ONE_WAY/oneway=-1/g' 's/osmIdentifier/@id/g')
for i in ${replace[@]}; do
	find clarified -type f -depth 1 -name '*.geojson' -exec sed -e "${i}" -i '' {} \;
done
