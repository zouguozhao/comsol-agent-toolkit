function result = comsol_agent_livelink(host, port, tag, mli)
% 附着到现有 Server 并核对显式 Tag；不加载文件、覆盖模型或启动求解。
% 调用前检查 MATLAB、COMSOL LiveLink 与许可证；本工具包未实测此链路。
arguments
    host (1,:) char
    port (1,1) double {mustBeInteger, mustBePositive}
    tag (1,:) char
    mli (1,:) char
end
if port > 65535
    error('端口不能超过 65535。');
end
if ~isfolder(mli)
    error('LiveLink mli 目录不存在。');
end
addpath(mli);
mphstart(host, port);
import com.comsol.model.util.ModelUtil
tags = cell(ModelUtil.tags());
if ~any(strcmp(tags, tag))
    error('Server 中不存在所指定的模型 Tag。');
end
model = ModelUtil.model(tag);
result = struct('tag', char(model.tag()), 'label', char(model.label()), ...
    'filePath', char(model.getFilePath()), 'serverTags', {tags});
end
