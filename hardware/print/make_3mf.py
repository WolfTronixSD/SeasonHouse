"""Pack the five STLs into one Bambu Studio project (.3mf) with each part's
per-part settings (walls, infill, brim) in Bambu's model_settings.config, plus
the X2D / 0.20mm Standard / Bambu PLA Basic settings Bambu needs to accept them
(bambu_x2d_project_settings.json, flattened from Bambu Studio's profiles)."""
import os, uuid, zipfile
import numpy as np, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
BED = 256.0
# name: (x centre, y centre on the bed, per-part settings)
PARTS = {
    "spider_body":        (78, 128, dict(wall_loops="2", sparse_infill_density="15%", brim_type="outer_only")),
    "spider_battery_lid": (78, 226, dict(wall_loops="2", sparse_infill_density="15%", brim_type="outer_only")),
    "winch_bracket":      (198, 70, dict(wall_loops="4", sparse_infill_density="30%", sparse_infill_pattern="gyroid")),
    "winch_spool":        (180, 160, dict(wall_loops="4", sparse_infill_density="40%")),
    "slipring_cup":       (225, 160, dict(wall_loops="4", sparse_infill_density="40%")),
}
COMMON = dict(layer_height="0.2", enable_support="0")


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def main(out=os.path.join(HERE, "seasonhouse_spider.3mf")):
    objs, comps, build, cfg, inst = [], [], [], [], []
    for i, (name, (cx, cy, s)) in enumerate(PARTS.items()):
        oid, pid = 2 * i + 2, 2 * i + 1
        m = trimesh.load(os.path.join(HERE, name + ".stl"), process=False)
        lo, hi = m.bounds
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        assert hi[0] - lo[0] < BED and hi[1] - lo[1] < BED
        objs.append(f'<object id="{pid}" p:UUID="{uuid.uuid4()}" type="model">{mesh_xml(m)}</object>')
        comps.append(f'<object id="{oid}" p:UUID="{uuid.uuid4()}" type="model"><components>'
                     f'<component p:path="/3D/Objects/object_1.model" objectid="{pid}" p:UUID="{uuid.uuid4()}" '
                     f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object>')
        build.append(f'<item objectid="{oid}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 {cx} {cy} 0" printable="1"/>')
        meta = "".join(f'<metadata key="{k}" value="{v}"/>' for k, v in {**COMMON, **s}.items())
        cfg.append(f'<object id="{oid}"><metadata key="name" value="{name}"/><metadata key="extruder" value="1"/>{meta}'
                   f'<part id="{pid}" subtype="normal_part"><metadata key="name" value="{name}"/>'
                   f'<metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/></part></object>')
        inst.append(f'<model_instance><metadata key="object_id" value="{oid}"/>'
                    f'<metadata key="instance_id" value="0"/><metadata key="identify_id" value="{100 + i}"/></model_instance>')
    ns = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
          'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
          'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
            '<Default Extension="config" ContentType="text/xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        "3D/_rels/3dmodel.model.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        "3D/Objects/object_1.model": f'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" {ns}>'
            f'<metadata name="BambuStudio:3mfVersion">1</metadata><resources>{"".join(objs)}</resources><build/></model>',
        "3D/3dmodel.model": f'<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" {ns}>'
            '<metadata name="Application">BambuStudio-02.08.00.09</metadata><metadata name="BambuStudio:3mfVersion">1</metadata>'
            '<metadata name="Title">SeasonHouse corner spider</metadata>'
            f'<resources>{"".join(comps)}</resources><build p:UUID="{uuid.uuid4()}">{"".join(build)}</build></model>',
        "Metadata/model_settings.config": '<?xml version="1.0" encoding="UTF-8"?><config>' + "".join(cfg) +
            '<plate><metadata key="plater_id" value="1"/><metadata key="plater_name" value="Spider winch"/>'
            '<metadata key="locked" value="false"/>' + "".join(inst) + '</plate></config>',
    }
    # full X2D 0.4 printer + 0.20mm Standard + Bambu PLA Basic settings, flattened from
    # Bambu Studio's own profiles; Bambu rejects a project without them
    with open(os.path.join(HERE, "bambu_x2d_project_settings.json")) as f:
        files["Metadata/project_settings.config"] = f.read()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in files.items():
            z.writestr(k, v)
    print(out, os.path.getsize(out) // 1024, "kB")


if __name__ == "__main__":
    main()
