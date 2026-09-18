"""Execute the official DiffSynth paired Qwen-Image-Edit-2509 LoRA recipe.
Install DiffSynth from a reviewed commit on the GPU worker; see docs/TRAINING.md.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--diffsynth',type=Path,required=True);p.add_argument('--pairs',type=Path,default=ROOT/'data/pairs');p.add_argument('--output',type=Path,default=ROOT/'models/aqpix-lora');p.add_argument('--steps-epochs',type=int,default=5);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
summary=json.loads((a.pairs/'summary.json').read_text())
script=a.diffsynth.resolve()/'examples/qwen_image/model_training/train.py'
cmd=['accelerate','launch',str(script),'--dataset_base_path',str(a.pairs.resolve()),'--dataset_metadata_path',str((a.pairs/'train.json').resolve()),'--data_file_keys','image,edit_image','--extra_inputs','edit_image','--max_pixels','589824','--dataset_repeat','20','--model_id_with_origin_paths','Qwen/Qwen-Image-Edit-2509:transformer/diffusion_pytorch_model*.safetensors,Qwen/Qwen-Image:text_encoder/model*.safetensors,Qwen/Qwen-Image:vae/diffusion_pytorch_model.safetensors','--learning_rate','1e-4','--num_epochs',str(a.steps_epochs),'--remove_prefix_in_ckpt','pipe.dit.','--output_path',str(a.output.resolve()),'--lora_base_model','dit','--lora_target_modules','to_q,to_k,to_v,add_q_proj,add_k_proj,add_v_proj,to_out.0,to_add_out,img_mlp.net.2,img_mod.1,txt_mlp.net.2,txt_mod.1','--lora_rank','16','--use_gradient_checkpointing','--dataset_num_workers','2','--find_unused_parameters']
if a.dry_run:
    print(json.dumps({'dataset':summary,'command':cmd,'executed':False},indent=2));sys.exit(0)
if not summary['training_ready']:p.error('Dataset insuficiente: mínimo 30 pares de treino e 5 de validação. Os 3 exemplos são apenas smoke test.')
if not script.is_file():p.error('Checkout DiffSynth não encontrado')
import torch
if not torch.cuda.is_available():p.error('Treinamento exige GPU CUDA')
a.output.mkdir(parents=True,exist_ok=True)
revision=subprocess.check_output(['git','-C',str(a.diffsynth),'rev-parse','HEAD'],text=True).strip()
(a.output/'run.json').write_text(json.dumps({'command':cmd,'diffsynth_commit':revision,'dataset':summary},indent=2))
subprocess.run(cmd,cwd=a.diffsynth,check=True)
