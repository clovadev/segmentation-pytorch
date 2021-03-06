import os

import matplotlib.pyplot as plt
import torch.nn.functional as F
import torch.utils.data
import tqdm

import utils


if __name__ == '__main__':
    # Load cfg and create components builder
    cfg = utils.builder.load_cfg()
    builder = utils.builder.Builder(cfg)

    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # 1. Dataset
    valset, _ = builder.build_dataset('val')

    # 2. Model
    model = builder.build_model(valset.num_classes, pretrained=True).to(device)
    model_name = cfg['model']['name']
    amp_enabled = cfg['model']['amp_enabled']
    print(f'Activated model: {model_name}')

    # 이미지 불러오기
    image_number = input('Enter the image number of the dataset>>> ')
    if image_number == '':
        image_number = 0
    else:
        image_number = int(image_number)
    image, _ = valset[image_number]
    image = image.unsqueeze(0).to(device)

    # 모델의 각 계층에 특징맵을 받아오는 hook을 등록
    feature_maps = {}
    if model_name == 'UNet':
        model.encode1.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode1'))
        model.encode2.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode2'))
        model.encode3.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode3'))
        model.encode4.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode4'))
        model.encode_end.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode_end'))
        model.decode4.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode4'))
        model.decode3.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode3'))
        model.decode2.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode2'))
        model.decode1.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode1'))
        model.classifier.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'classifier'))
    elif model_name == 'AR_UNet':
        model.initial_conv.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'initial_conv'))
        model.encode1.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode1'))
        model.encode2.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode2'))
        model.encode3.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode3'))
        model.encode4.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'encode4'))
        model.aspp.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'aspp'))
        model.decode3.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode3'))
        model.decode2.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode2'))
        model.decode1.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'decode1'))
        model.classifier.register_forward_hook(utils.hooks.get_feature_maps_with_name(feature_maps, 'classifier'))
    else:
        raise NotImplementedError('Wrong model_name.')

    # 예측
    with torch.cuda.amp.autocast(enabled=amp_enabled):
        with torch.no_grad():
            output = model(image)

    # 각 계층의 feature maps 저장
    for layer in tqdm.tqdm(feature_maps.keys(), desc='Saving'):
        result_dir = os.path.join('feature_maps', model_name, layer)
        os.makedirs(result_dir, exist_ok=True)
        feature_map = feature_maps[layer].squeeze().cpu()
        if layer == 'classifier':
            feature_map = F.log_softmax(feature_map, dim=0)

        for i in tqdm.tqdm(range(feature_map.size()[0]), desc='Channels', leave=False):
            plt.imsave(os.path.join(result_dir, '{}.png'.format(i + 1)), feature_map[i])
