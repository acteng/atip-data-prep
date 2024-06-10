This script converts an internal Excel file with all collected critical issues
and policy conflicts into a GeoJSON layer.

1.  `npm i`
2.  Download the latest version of <https://departmentfortransportuk.sharepoint.com/:x:/r/sites/ATE/Inspectorate/DA_Log.xlsx?d=wa248cc0a6ca04987a1c600cc7dcd932e&csf=1&web=1&e=WBf855>
3.  `npm run convert DA_Log.xlsx`
4.  `gsutil cp problems.geojson.gz gs://dft-rlg-atip-test/private_layers/v1/`
