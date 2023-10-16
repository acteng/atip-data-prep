const mapshaper = require('mapshaper');

const cmd = '-i input/local_authority_districts_reprojected.geojson input/transport_authorities_reprojected.geojson merge-files -o output/authorities.geojson'

mapshaper.runCommands(cmd, () => {
    console.log('Concat finsihed')
});


