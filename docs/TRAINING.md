# Treinamento e lote em CUDA

## O que existe

Três pares reais foram salvos para Brachygobius doriae, Neocaridina davidi Red Sakura e Anubias barteri nana. O professor foi o ImageGen integrado ao Codex. Os prompts originais estão em `data/references/*.prompt.txt`; não foram gerados por um Qwen já ajustado. O replay offline não chama o professor novamente.

`prepare_pairs.py` produz metadados no formato `image` (target), `edit_image` (lista de condições) e `prompt` da [receita oficial DiffSynth](https://github.com/modelscope/DiffSynth-Studio/blob/main/examples/qwen_image/model_training/lora/Qwen-Image-Edit-2509.sh). É treinamento de edição condicionado à foto; não é DreamBooth de texto para imagem. A [validação oficial](https://github.com/modelscope/DiffSynth-Studio/blob/main/examples/qwen_image/model_training/validate_lora/Qwen-Image-Edit-2509.py) carrega o adaptador no mesmo runtime. O backend `diffsynth` segue esse caminho, evitando assumir que pesos DiffSynth são intercambiáveis com Diffusers.

## Preparação

1. Expandir referências para pelo menos 40–100 pares cobrindo peixes alongados/discoides, nadadeiras longas, espécies escuras/claras, camarões e plantas. O mínimo de 30 treino + 5 validação é apenas uma barreira operacional, não garantia estatística.
2. Salvar cada edição em `data/references/<id>.png`, preservando foto e prompt do professor. O ID é SHA-256 da URL truncado em 16 caracteres; `load_catalog()` fornece IDs.
3. Processar esses IDs com `python -m aquarium.cli sprites --backend reference --ids ...`.
4. Rever anatomia, isolamento, marcações e vista lateral. O QA automático verifica apenas propriedades de raster.
5. Executar `python scripts/prepare_pairs.py`. O split agrupa pelo nome científico, evitando vazamento entre variantes. Com apenas três pares o resultado entregue é 2 treino / 1 validação e `training_ready: false`.

O treinamento fornecido condiciona à fotografia única. As referências extras de estilo são opcionais na inferência; para usá-las sistematicamente, adicionar as mesmas referências fixas a `edit_image` em todas as linhas de treino e validação, incluindo legendas de papel de cada imagem, e comparar com a configuração de uma imagem. Não usar o target da própria espécie como referência de entrada: isso vazaria a resposta.

## Worker

Usar Linux, Python 3.11, PyTorch compatível com a versão CUDA da máquina. Clonar o [repositório oficial DiffSynth-Studio](https://github.com/modelscope/DiffSynth-Studio), revisar e fixar um commit; instalar conforme as instruções desse checkout. O launcher registra o commit usado em `models/aqpix-lora/run.json`. Como este ambiente não tem CUDA, nenhuma revisão foi certificada por execução GPU nesta entrega. Não instalar por conveniência a versão de desenvolvimento sem registrar o commit.

```bash
python scripts/train_lora.py --diffsynth /opt/DiffSynth-Studio --dry-run
python scripts/train_lora.py --diffsynth /opt/DiffSynth-Studio
```

O dry-run já foi executado e está em `data/training-dry-run.json`. O comando real recusa o dataset de três pares. A GPU, os pesos base e um dataset suficiente são pré-requisitos ainda pendentes. O treino usa LoRA rank 16, learning rate 1e-4, gradient checkpointing, pares 768×768 e 5 épocas; são hiperparâmetros iniciais a ajustar por validação, não uma configuração já otimizada.

## Validação antes do lote

```bash
python scripts/smoke_sprites.py --backend diffsynth \
  --lora models/aqpix-lora/epoch-4.safetensors --out data/qwen-smoke
```

Usar o checkpoint realmente produzido pelo treino; o nome acima segue a convenção da receita. Comparar exemplos retidos, especialmente espécies fora dos pares de treinamento. Verificar direção, silhueta, olhos/antenas/nadadeiras/raízes, identidade, halos e legibilidade a 1×/2×. Os 3 exemplos do smoke são um teste técnico conhecido, não substituem validação em espécies inéditas.

Para usar o modelo base via Diffusers sem adaptador:

```bash
python scripts/smoke_sprites.py --backend qwen --out data/base-qwen-smoke
```

Somente depois de validar o modelo:

```bash
python scripts/refresh.py --backend diffsynth \
  --lora models/aqpix-lora/epoch-4.safetensors --out data/production
```

O fluxo faz o smoke primeiro, interrompe se falhar, depois processa os itens elegíveis em lote; gera o índice e exporta sprites para a extensão. Repetir o comando reusa o cache. `--backend qwen` usa Diffusers; `--backend diffsynth` usa os adaptadores da receita de treino. Nunca passar pesos DiffSynth a Diffusers sem conversão e validação explícitas.

## Limites visuais conhecidos

A Anúbia gerada pelo professor veio com xadrez cinza desenhado, sem alpha. O pipeline remove o fundo neutro e aplica alpha binário. Esse fallback funciona para esta planta, mas pode remover tons cinza de outro organismo quando houver xadrez opaco; preferir alpha verdadeiro/fundo branco e inspecionar novos casos. Não é segmentação universal de fotografias: a remoção é aplicada à saída estilizada do modelo, nunca apresentada como conversão suficiente da foto em pixel art.

A paleta é global e pode aproximar cores raras. A luz e o ângulo são prescritos por prompt; garantias rígidas exigiriam pose/segmentação condicionada ou um verificador visual calibrado, ainda não implementado. A animação da extensão movimenta o sprite inteiro; não há frames de nado gerados.
