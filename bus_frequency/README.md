# Bus stop frequencies

This produces a layer with points for every bus stop in England, with a count
of buses stopping there during the most peak hour for that stop.

Go to <https://data.bus-data.dft.gov.uk/timetable/download/>, then choose "All
- Download timetables data in GTFS format". You have to register for an
account. Unzip the file somewhere.

Then `cargo run --release ~//Downloads/uk_gtfs`, passing in the path of the
unzipped directory.

Turn into pmtiles:

```
time tippecanoe stops.geojson \
	--force \
	--generate-ids \
	-l bus_stops \
	-zg \
	--drop-densest-as-needed \
	--extend-zooms-if-still-dropping \
	-o bus_stops.pmtiles
```
