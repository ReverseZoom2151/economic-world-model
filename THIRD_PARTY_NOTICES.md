# Third-party data notices

## Natural Earth Admin 0 Countries

- Dataset: Natural Earth, Admin 0 Countries, 1:110m Cultural Vectors
- Version: 5.1.1
- License: public domain under the Natural Earth terms of use
- Official dataset page: <https://www.naturalearthdata.com/downloads/110m-cultural-vectors/>
- Terms of use: <https://www.naturalearthdata.com/about/terms-of-use/>
- Pinned source: `natural-earth-vector` tag `v5.1.1`, commit `9380cca83db5f9aef52d5e762765100745f84b27`
- Pinned source URL: <https://github.com/nvkelso/natural-earth-vector/blob/v5.1.1/geojson/ne_110m_admin_0_countries.geojson>
- Source file: `geojson/ne_110m_admin_0_countries.geojson`
- Source SHA-256: `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`
- Derived asset: `workbench/src/assets/natural-earth-110m.json`
- Derived asset SHA-256: `03745cb43ae019ff1bca63b1b781d83a3ff3fa89af5d0d69768b0e6d3ac3a148`
- Transformation: retain geometry, feature identity, `NAME`, and `ADM0_A3`; remove unrelated properties; serialize deterministically without coordinate inference or boundary modification

Natural Earth boundaries are a visual reference layer. They are not evidence that an economic object belongs to a jurisdiction, and disputed boundaries do not express a position by this project.
