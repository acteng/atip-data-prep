The quick debugging approach:

osmium tags-filter ~/cloudflare_sync/severance_pbfs/liverpool.pbf nw/highway,footway,cycleway=crossing -o crossings.pbf

osmium export crossings.pbf -o crossings.geojson --attributes=id,way_nodes
