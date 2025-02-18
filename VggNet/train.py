import os
import json

import torch
import torch.nn as nn
from torchvision import transforms, datasets
import torch.optim as optim
from tqdm import tqdm
from model import vgg

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("using {} device".format(device))
    data_transform = {
        "train": transforms.Compose([transforms.RandomResizedCrop(224), 
                                    transforms.RandomHorizontalFlip(),
                                    transforms.ToTensor(),
                                    transforms.Normalize((0.5,0.5,0.5), (0.5, 0.5, 0.5))]),
        "val": transforms.Compose([transforms.Resize(224, 224), 
                                   transforms.ToTensor(),
                                   transforms.Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))])
    }
    data_root = os.path.abspath(os.path.join(os.getcwd(), "../.."))  # get data root path
    image_path = os.path.join(data_root, "VggNet", "data_set", "flower_data")  # flower data set path
    assert os.path.exists(image_path), "{} path does not exist.".format(image_path)
    train_dataset = datasets.ImageFolder(root=os.path.join(image_path, "train"),
                                         transform=data_transform["train"])
    train_num = len(train_dataset)
    # {'daisy':0, 'dandelion':1, 'roses':2, 'sunflower':3, 'tulips':4}
    flower_list = train_dataset.class_to_idx
    cla_dict = dict((val, key) for key, val in flower_list.items())
    # write dict into json file
    json_str = json.dumps(cla_dict, indent=4)
    with open('.\VggNet\class_indices.json', 'w') as json_file:
        json_file.write(json_str)
    
    batch_size=32
    nw = min([os.cpu_count(), batch_size if batch_size > 1 else 0, 8])  # number of workers
    print('Using {} dataloader workers every process'.format(nw))

    train_loader = torch.utils.data.DataLoader(train_dataset, 
                                               batch_size=batch_size, 
                                               shuffle=True, 
                                               num_workers=nw)

    validate_dataset = datasets.ImageFolder(root=os.path.join(image_path, "val"),
                                            transform=data_transform["val"])
    val_num = len(validate_dataset)
    validate_loader = torch.utils.data.DataLoader(validate_dataset,
                                                  batch_size=batch_size, shuffle=False,
                                                  num_workers=nw)
    print("using {} images for training, {} images for validation.".format(train_num,
                                                                           val_num))  
    model_name = "vgg16"
    net = vgg(model_name=model_name, num_classes=5, init_weights=True)
    net.to(device)
    loss_function = nn.CrossEntropyLoss()
    optimizer = optim.Adam(net.parameters(),lr=0.0001)

    epochs=10
    # 模型保存路径
    save_path = './VggNet/{}Net.pth'.format(model_name)
    # 记录模型最高准确率
    best_acc = 0.0
    # 这里的steps = 训练(验证)集数据总量 / 训练(验证)集的batch_size。也就是按照batch_size去读数据，需要读多少次
    train_steps = len(train_loader)
    validate_steps = len(validate_loader)
    for epoch in range(epochs):
        # train
        net.train()
        training_loss=0.0
        validate_loss=0.0
        # 利用tqdm为数据读取中，提供进度条显示，有可视化与提醒作用
        # 用法：tqdm(data_loader)
        train_bar = tqdm(train_loader)
        for step, data in enumerate(train_bar):
            images, labels = data
            optimizer.zero_grad()
            outputs=net(images.to(device))
            train_step_loss = loss_function(outputs, labels.to(device))
            train_step_loss.backward()
            optimizer.step()

            # training_loss记录的是每个epoch的总loss，train_step_loss记录的是一个epoch里每个bath_size的loss
            training_loss += train_step_loss.item()
            # desc功能，显示进度条的同时输出每个epoch里，每个batch_size的loss
            train_bar.desc = "train epoch[{}/{}] loss:{:.3f}".format(epoch+1, epochs, train_step_loss)

        # validate
        net.eval()
        acc = 0.0
        with torch.no_grad():
            val_bar = tqdm(validate_loader)
        for val_data in val_bar:
            val_images, val_labels = val_data
            outputs = net(val_images.to(device))
            validate_step_loss = loss_function(outputs, val_labels.to(device))
            predict_y = torch.max(outputs, dim=1)[1]
            acc += torch.eq(predict_y, val_labels.to(device)).sum().item()
            validate_loss += validate_step_loss.item()
            val_bar.desc = "validate epoch[{}/{}] loss:{:.3f}".format(epoch+1, epochs, validate_step_loss)
        val_accuracy = acc / val_num

        # 每个epoch总结一次，输出train_loss和validate_loss的平均loss以及在验证机上的准确率
        print('[epoch %d] train_loss: %.3f validate_loss: %.3f val_accuracy: %.3f' % 
            (epoch+1, training_loss/train_steps, validate_loss/validate_steps, val_accuracy))
        
        # 如果该epoch训练出来的模型在验证集上的准确率比最高的acc要高，怎保存该准确率并且保存该模型
        if val_accuracy > best_acc:
            best_acc = val_accuracy
            torch.save(net.state_dict(), save_path)
        
    print('Finished Training')


if __name__ == '__main__':
    main()    
