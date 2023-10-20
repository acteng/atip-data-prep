import mapshaper from 'mapshaper';

const cmd = '-i input/transport_authorities_reprojected.geojson input/local_authority_districts_reprojected.geojson merge-files -o tmp/authorities.geojson'

mapshaper.runCommands(cmd, () => {
    console.log('Concat finsihed')
    const cmd = '-i tmp/authorities.geojson -simplify 1.5% -o output/authorities.geojson'
    
    mapshaper.runCommands(cmd, () => {
        console.log("Local and Transport Authorities finished");
    });
});
