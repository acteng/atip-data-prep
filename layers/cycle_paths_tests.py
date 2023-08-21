import cycle_paths
import unittest


class TestGetProps(unittest.TestCase):
    def test_getProps(self):
        # You can generate entries using ../osm_unit_test_tool.html. The output
        # is [kind, direction, width]. You can manually remove very irrelevant
        # tags (like name) at your own discretion
        for testCase in [
            {
                "id": "29063778",
                "tags": ["highway=cycleway", "oneway=yes", "sidewalk=left"],
                "output": ["track", "one-way", "unknown"],
            },
            {
                "id": "256017834",
                "tags": [
                    "bicycle=designated",
                    "foot=designated",
                    "highway=cycleway",
                    "segregated=yes",
                ],
                "output": ["shared_use_segregated", "unknown", "unknown"],
            },
        ]:
            tags = {}
            for tag in testCase["tags"]:
                key, value = tag.split("=")
                tags[key] = value
            tags["@id"] = testCase["id"]

            actualResult = cycle_paths.getProps(tags)

            kind, direction, width = testCase["output"]
            expectedResult = {
                "kind": kind,
                "direction": direction,
                "width": width,
                "osm_id": testCase["id"],
            }

            self.assertEqual(actualResult, expectedResult)


if __name__ == "__main__":
    unittest.main()
