# A/B Street to ATIP import

This repo has some initial experiments to export data from A/B Street's import
process to whatever ATIP will need. In the future, this would probably be based
on `osm2streets` instead. Maybe it'll run as an offline import process, maybe
it'll happen client-side dynamically as needed, maybe it'll evolve into a very
elaborate two-way conflation and sync between upstream OSM data and ATIP.

Note on submodules: after cloning this repo, you have to `git submodule init;
git submodule update` before the `route_snapper` code works
