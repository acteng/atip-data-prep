const mapshaper = require('mapshaper');
const fs = require('fs/promises');
const csv = require('csv-parser');

const getLadNameArray = (ladNameString) => {
    return (ladNameString.split(', '));
}

const checkLadNameAndAddTransportAuthority = (ladName, ladData, transportAuthority) => {
    if (ladName === ladData.LAD23NM) {
        ladData.transport_authority_name = transportAuthority.atf4_authority_name;
        ladData.localAuthorities = transportAuthority.lad_names;
        return true;
    }
    return false;
}

const addTransportAuthorityToLocalAuthorities = (transport_authorities, lads) => {
    transport_authorities.features.forEach((transport_authority) => {
        const ladNameArray = getLadNameArray(transport_authority.properties.lad_names);
        transport_authority.properties.lad_names = ladNameArray;
        ladNameArray.forEach((ladName) => {
            var ladFound = false;
            var i = 0;
            while (!ladFound && i < lads.features.length) {
                ladFound = checkLadNameAndAddTransportAuthority(ladName, lads.features[i++].properties, transport_authority.properties);
            }
        });
    });
}

const mergeLADsWithTheSameTA = (ladsTmpFile) => {
    const cmd = `-i ${ladsTmpFile} -dissolve2 fields=transport_authority_name gap-fill-area=5km2 allow-overlaps -o ${ladsTmpFile}`

    mapshaper.runCommands(cmd, () => {

        const cmd = `-i ${ladsTmpFile} -simplify 1.5% -o output/transportAuthoritiesExtentOfRealm.geojson`;

        mapshaper.runCommands(cmd, () => {
            console.log("Transport authorities finished");
        });
    });
}

fs.readFile('input/transport_authorities.geojson')
    .then((trasnport_authority_data) => {
        fs.readFile('input/Local_Authority_Districts_May_2023_UK_BFE_V2_-8925004851483419689.geojson')
            .then((lad_data) => {
                const transport_authorities = JSON.parse(trasnport_authority_data);
                const lads = JSON.parse(lad_data);
                addTransportAuthorityToLocalAuthorities(transport_authorities, lads);
                lads.features = lads.features.filter((feature) => {
                    return feature.properties.transport_authority_name;
                })


                const ladsTmpFile = 'tmp/localAuthorities.geojson';
                fs.writeFile(ladsTmpFile, JSON.stringify(lads))
                    .then(() => {
                        mergeLADsWithTheSameTA(transport_authorities, ladsTmpFile);
                    });
            });
    });

const cmd = '-i input/Local_Authority_Districts_May_2023_UK_BFE_V2_-8925004851483419689.geojson -simplify 1.5% -o output/localAuthoritiesExtentOfRealm.geojson'

mapshaper.runCommands(cmd, () => {
    console.log("Local authorities finished");
});


