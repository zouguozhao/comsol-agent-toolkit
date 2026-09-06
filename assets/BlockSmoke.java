import com.comsol.model.Model;
import com.comsol.model.util.ModelUtil;

/** 工具自检：建立参数化立方体和网格，不定义焊接工况或进行物理求解。 */
public class BlockSmoke {
    public static Model run() {
        Model model = ModelUtil.create("ToolkitBlockSmoke");
        model.label("toolkit_block_smoke.mph");
        model.param().set("L", "10[mm]");
        model.component().create("comp1", true);
        model.component("comp1").geom().create("geom1", 3);
        model.component("comp1").geom("geom1").lengthUnit("mm");
        model.component("comp1").geom("geom1").create("blk1", "Block");
        model.component("comp1").geom("geom1").feature("blk1")
            .set("size", new String[]{"L", "L", "L"});
        model.component("comp1").geom("geom1").run();
        model.component("comp1").mesh().create("mesh1");
        model.component("comp1").mesh("mesh1").autoMeshSize(8);
        model.component("comp1").mesh("mesh1").run();
        System.out.println("TOOLKIT_MODEL_TAG=" + model.tag());
        System.out.println("TOOLKIT_LENGTH=" + model.param().get("L"));
        System.out.println("TOOLKIT_GEOMETRY_BUILT=true");
        System.out.println("TOOLKIT_MESH_ELEMENTS=" + model.component("comp1").mesh("mesh1").getNumElem());
        return model;
    }

    public static void main(String[] args) {
        run();
    }
}
