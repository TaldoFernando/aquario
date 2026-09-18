# Transformar fotos em pixel art com Qwen/Qwen-Image

Este pacote executa **exatamente `Qwen/Qwen-Image`** com `QwenImageImg2ImgPipeline`, usando a foto como estado inicial da difusão e um prompt de pixel art. É uma configuração de inferência com pesos pré-treinados; não inclui um novo checkpoint treinado nem troca silenciosamente para Qwen Image Edit.

A implementação segue o [exemplo oficial do Diffusers 0.36.0](https://github.com/huggingface/diffusers/blob/v0.36.0/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_img2img.py). O [modelo solicitado](https://huggingface.co/Qwen/Qwen-Image) tem 20 bilhões de parâmetros. Este fluxo permite transformar a foto, mas não garante a mesma fidelidade semântica de um modelo especializado em edição. `strength` alto pode alterar anatomia e marcações; avaliar as três espécies antes de ampliar.

## Rodar sem configurar tudo no Mac

Abra `notebooks/Qwen_Pixel_Art.ipynb` no Jupyter de uma máquina NVIDIA/CUDA ou importe no Colab. Envie `dist/aquario-qwen.zip` quando a primeira célula solicitar. O notebook instala dependências, verifica CUDA, executa o smoke de três fotos e mostra os resultados. Não é preciso treinar antes do primeiro teste. Uma GPU pequena do Colab gratuito pode não comportar o modelo; o notebook não promete que uma T4 seja suficiente.

O ZIP inclui código, configuração, catálogo e as três fotos. **Não inclui pesos**. Qwen e, se usada, a segmentação rembg são baixados na primeira execução. Não envia suas fotos para uma API de imagem: a inferência ocorre na máquina onde você roda o script. Ao usar Colab/VM, os arquivos ficam nessa máquina remota.

## Rodar pelo terminal

Use Python 3.11. Em Mac Apple Silicon, PyTorch pode usar MPS; em Linux, use uma instalação com PyTorch/CUDA. Na pasta extraída:

```bash
python3 -m venv .venv-qwen
source .venv-qwen/bin/activate
python3 -m pip install -r requirements-qwen.txt

# Ver entradas e parâmetros, sem GPU e sem baixar pesos
python3 scripts/qwen_pixelart.py --dataset kauar_peixes.json --smoke --dry-run

# Testar as três espécies reais (Abelhinha, Red Sakura, Anúbia)
python3 scripts/qwen_pixelart.py --dataset kauar_peixes.json --smoke \
  --remove-background --output output/teste-qwen

# No Mac Apple Silicon, force Metal se necessário
python3 scripts/qwen_pixelart.py --dataset kauar_peixes.json --smoke \
  --device mps --resolution 512 --remove-background --output output/teste-qwen
```

Foto avulsa:

```bash
python3 scripts/qwen_pixelart.py \
  --input data/sources/fd6fb795dbc0c857.png \
  --subject "Brachygobius doriae, small yellow goby with black vertical stripes" \
  --strength 0.65 --remove-background --output output/meu-peixe
```

Pasta de fotos (somente arquivos do primeiro nível):

```bash
python3 scripts/qwen_pixelart.py --input minhas-fotos \
  --subject "aquarium fish" --remove-background --output output/pasta
```

Todas as entradas elegíveis do catálogo, depois de avaliar o smoke:

```bash
python3 scripts/qwen_pixelart.py --dataset kauar_peixes.json --all \
  --remove-background --output output/catalogo-qwen
```

Sem `--all` ou `--smoke`, o catálogo processa os primeiros 3 itens elegíveis; `--limit 10` altera o limite. Uma pasta processa todas as fotos reconhecidas. O catálogo tem 651 registros e 603 candidatos depois da triagem de promoções; não são todos táxons distintos. A execução não modifica as fotos nem o JSON original.

## Ajustes

| Opção | Padrão | Efeito |
|---|---|---|
| `--strength` | 0.65 | Menor preserva mais a foto; maior muda mais o estilo e pode perder identidade |
| `--steps` | 40 | Passos nominais; img2img usa uma fração conforme strength |
| `--resolution` | 768 | Resolução de inferência; o sprite final continua 96×96 |
| `--cfg` | 4.0 | Peso de orientação pelo texto; maior não garante melhor imagem |
| `--seed` | 42 | Base para seed determinística por item |
| `--offload` | model | `model`, `sequential` ou `none` |
| `--device` | auto | `auto`, `cuda`, `mps` ou `cpu`; `auto` prioriza CUDA e depois MPS |
| `--remove-background` | desligado | Segmenta a foto antes e a arte depois com rembg/ISNet em CPU |
| `--revision` | main | Use hash de commit do modelo para fixar os pesos |
| `--lora` | nenhum | Adaptador local compatível com Qwen-Image/Diffusers, se disponível |
| `--force` | desligado | Refaz mesmo quando há saída em cache válida |

Comece com 0.55–0.7. Se o peixe perder marcações, reduza strength; se parecer apenas uma foto pixelada, aumente aos poucos. Esses valores são um ponto de partida, ainda não calibrado em GPU neste projeto. Para foto avulsa, descreva espécie e cores em `--subject`; o script não usa um reconhecedor automático de espécies.

A remoção de fundo ajuda a evitar que o cenário original sobreviva à difusão. O segmentador genérico pode perder antenas, nadadeiras transparentes ou raízes: nesse caso, forneça um PNG já recortado e omita `--remove-background`. Sem segmentação, o normalizador tenta remover fundo neutro. Se a saída ainda tiver cenário, o job falha com mensagem e mantém `.raw.png`, sem declarar sucesso falso.

Prompt e parâmetros padrão: `config/qwen_pixelart.json`. Paleta, margem e grid: `config/style.json`. Os prompts deste caminho descrevem a imagem desejada, sem alegar que o modelo base possui condicionamento semântico multi-imagem do Qwen Edit.

## Arquivos produzidos

Para cada item:

- `<id>.input.png`: foto preparada para a difusão, com enquadramento preservado.
- `<id>.raw.png`: saída real do Qwen, antes do processamento de sprite.
- `<id>.png`: sprite RGBA 96×96 com paleta e contorno padronizados.
- `<id>.preview.png`: ampliação 4× por nearest-neighbor.
- `<id>.json`: modelo, configurações, hash da foto, prompt, seed, ambiente, duração e QA.
- `<id>.error.json`: registro de falha, quando houver; pode permanecer como histórico após uma tentativa posterior bem-sucedida. O status vigente está no `.json` e no `report.json`.

`report.json` resume sucesso/cache/falha; falha por item retorna código 1, configuração/ambiente retorna 2. Os resultados são armazenados separadamente dos sprites do professor já existentes. Este novo comando não publica nem substitui assets da extensão automaticamente.

Repetir o comando reutiliza saídas válidas com os mesmos parâmetros e conteúdo de entrada. Alterar strength, prompt, paleta, foto ou LoRA invalida o cache. Com `--revision main`, mudanças futuras no repositório remoto não invalidam o cache automaticamente: use um commit fixo ou `--force`. As fotos baixadas do catálogo também ficam em cache por URL; para atualizar conteúdo substituído no mesmo endereço, remover o PNG e sidecar correspondentes em `data/sources/`.

## Memória e plataforma

O alvo desta implementação é NVIDIA/CUDA. Em BF16, só 20B parâmetros correspondem a cerca de 40 GB; text encoder, VAE, ativações e cópias elevam o total. Como planejamento inicial, uma GPU de 80 GB e RAM abundante (64–128 GB) simplificam o primeiro teste, mas isso é estimativa de capacidade, não medição deste pacote. Deixe espaço de disco para dezenas de GB de pesos e cache. Não foi alugado nenhum recurso.

`--offload model` move componentes inteiros: o transformer ainda precisa caber na GPU durante sua execução. `--offload sequential` reduz a residência em VRAM e aumenta muito o tráfego CPU/GPU e o tempo; não garante execução em 8/16/24 GB. Se houver OOM, tente sequential e resolução 512 antes de avaliar hardware maior. O script não implementa quantização 4-bit.

Em Mac Apple Silicon, `--device auto` usa MPS quando disponível. `--offload model` e `--offload sequential` também tentam descarregar componentes do MPS para a RAM; `--offload none` mantém o pipeline no dispositivo. O Qwen-Image tem cerca de 20 bilhões de parâmetros e não é um modelo leve: em um Mac com 24 GiB, como o M5 Pro deste ambiente, mesmo o offload pode falhar por memória. A mensagem `MPS backend out of memory` não é corrigida por reduzir apenas a resolução. Para executar localmente, é necessário ter memória suficiente ou usar uma versão quantizada compatível; caso contrário, use uma GPU CUDA com memória adequada. O aviso `NotOpenSSLWarning` do Python 3.9/LibreSSL é separado e não causa o OOM.

## O que foi validado aqui

- Seleção das três espécies e planejamento sem download.
- Passagem da foto, strength, seed e CFG ao contrato img2img.
- Preparação de alpha/proporção, cache, alteração do arquivo de origem, recuperação de sprite corrompido e preservação da arte bruta em falhas.
- Testes locais com doubles de inferência explicitamente limitados aos testes.

**Não executado aqui:** download dos pesos Qwen, inferência em CUDA e avaliação visual de saídas desse modelo. As três artes anteriores do projeto foram produzidas por outro professor; não são apresentadas como resultados deste runner. O preset é pronto para teste em GPU, não um modelo de estilo fine-tunado.
