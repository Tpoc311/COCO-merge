import json
import shutil
from argparse import ArgumentParser, Namespace
from datetime import datetime
from os import listdir, mkdir, remove
from os.path import join, exists
from typing import Dict, Any, NoReturn, Optional


def add_coco_info(coco_file: dict, args: Namespace) -> Dict[str, any]:
    """
    Adds info to COCO annotation file.

    Args:
        coco_file: file into which info will be added.
        args: args passed into script.
    Returns:
    """
    coco_file['info']['contributor'] = args.contributor
    coco_file['info']['date_created'] = datetime.utcnow().isoformat(' ')
    coco_file['info']['description'] = args.description
    coco_file['info']['url'] = args.url
    coco_file['info']['version'] = args.version
    coco_file['info']['year'] = args.year

    coco_file['licenses'][0]['id'] = ''
    coco_file['licenses'][0]['name'] = ''
    coco_file['licenses'][0]['url'] = ''

    return coco_file


def coco_merge(input_extend: str, input_add: str, output_file: str, indent: Optional[int] = None) -> str:
    """Merge COCO annotation files.

    Args:
        input_extend: Path to input file to be extended.
        input_add: Path to input file to be added.
        output_file : Path to output file with merged annotations.
        indent: Argument passed to `json.dump`. See https://docs.python.org/3/library/json.html#json.dump.
    """
    with open(input_extend, "r") as f:
        data_extend = json.load(f)
    with open(input_add, "r") as f:
        data_add = json.load(f)

    output: Dict[str, Any] = {
        k: data_extend[k] for k in data_extend if k not in ("images", "annotations")
    }

    output["images"], output["annotations"] = [], []

    output = add_coco_info(coco_file=output, args=args)

    for i, data in enumerate([data_extend, data_add]):

        print("Input {}: {} images, {} annotations".format(i + 1, len(data["images"]), len(data["annotations"])))

        cat_id_map = {}
        for new_cat in data["categories"]:
            new_id = None
            for output_cat in output["categories"]:
                if new_cat["name"] == output_cat["name"]:
                    new_id = output_cat["id"]
                    break

            if new_id is not None:
                cat_id_map[new_cat["id"]] = new_id
            else:
                new_cat_id = max(c["id"] for c in output["categories"]) + 1
                cat_id_map[new_cat["id"]] = new_cat_id
                new_cat["id"] = new_cat_id
                output["categories"].append(new_cat)

        img_id_map = {}
        for image in data["images"]:
            n_imgs = len(output["images"])
            img_id_map[image["id"]] = n_imgs
            image["id"] = n_imgs

            output["images"].append(image)

        for annotation in data["annotations"]:
            n_anns = len(output["annotations"])
            annotation["id"] = n_anns
            annotation["image_id"] = img_id_map[annotation["image_id"]]
            annotation["category_id"] = cat_id_map[annotation["category_id"]]

            output["annotations"].append(annotation)

    print("Result: {} images, {} annotations".format(len(output["images"]), len(output["annotations"])))

    with open(output_file, "w") as f:
        json.dump(output, f, indent=indent)

    return output_file


def merge_datasets(args: Namespace) -> NoReturn:
    """
    Merges each folder with annotation.
    Args:
        args: args passed into script.
    Returns: NoReturn.
    """
    file_count = 0
    for folder in listdir(args.tobe_merged_path):
        # Check if folder is real folder (not file)
        if len(folder.split('.')) == 1:
            annot_path = join(args.tobe_merged_path, folder, 'lbl', 'COCO_annotation.json')
            data = json.load(open(annot_path))
            for image in data['images']:
                file_path = join(args.tobe_merged_path, folder, image['file_name'])
                if exists(file_path):
                    new_image_name = 'IMG_' + str(file_count) + '.jpg'
                    shutil.copy(join(args.tobe_merged_path, folder, image['file_name']),
                                join(args.merged_path, new_image_name))
                    file_count += 1
                    image['file_name'] = new_image_name
            new_annotation_name = folder + '.json'
            with open(join(args.merged_path, 'lbl', new_annotation_name), 'w') as f:
                json.dump(data, f)

    # Merge annotation files
    lbl_path = join(args.merged_path, 'lbl')
    merged_file_path = join(lbl_path, 'COCO_annotation.json')

    annot_files = listdir(lbl_path)
    shutil.copy(join(lbl_path, annot_files[0]), merged_file_path)
    for lbl_file in annot_files[1:]:
        coco_merge(merged_file_path, join(lbl_path, lbl_file), merged_file_path)

    # Remove temporary files
    for lbl_file in listdir(lbl_path):
        if lbl_file != 'COCO_annotation.json':
            remove(join(lbl_path, lbl_file))


if __name__ == "__main__":
    arguments = ArgumentParser(description='Merges COCO datasets.')
    arguments.add_argument('-tbmp', '--tobe_merged_path', type=str, help='Path to folder with datasets to be merged.')
    arguments.add_argument('-mp', '--merged_path', type=str, help='Path to save merged dataset')
    arguments.add_argument('-d', '--description', type=str,
                           help='Dataset description (task, type of objects on images, changes etc...)', default='')
    arguments.add_argument('-v', '--version', type=str, help='Dataset version', default='')
    arguments.add_argument('-y', '--year', type=str, help='Dataset create year', default='')
    arguments.add_argument('-c', '--contributor', type=str, help='Contributor', default='')
    arguments.add_argument('-url', '--url', type=str, help='URL', default='')
    args = arguments.parse_args()

    if exists(args.merged_path):
        if not exists(join(args.merged_path, 'lbl')):
            mkdir(join(args.merged_path, 'lbl'))
        print('Merging...')
        merge_datasets(args=args)
    else:
        print(f'Path {args.merged_path} does not exists!')
    print('Done!')
