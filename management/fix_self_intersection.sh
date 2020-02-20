#!/usr/bin/env sh
set -ex

DIR=$(dirname "${1}")
cd "${DIR}"
FILE=$(basename "${1}")
ogrinfo -dialect sqlite -sql "select * from \"${FILE%.*}\" where ST_IsValid(geometry)=0" "${FILE}"

#ogr2ogr -f GeoJSON -dialect sqlite -sql "select ST_MakeValid(geometry),STATEFP10,ZCTA5CE10,GEOID10,CLASSFP10,MTFCC10,FUNCSTAT10,ALAND10,AWATER10,INTPTLAT10,INTPTLON10,PARTFLG10 from \"${FILE%.*}\"" "clean_${FILE}" ${FILE}
