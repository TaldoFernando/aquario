# Validação realizada

## Resultados

- Smoke de sprites: **3/3** a partir das fotos do catálogo e edições produzidas por ImageGen. Peixe Abelhinha, Camarão Red Sakura, Anúbia Nana. Arquivos 96×96 RGBA, alpha 0/255, paleta de `config/style.json`, margem e contorno verificados.
- Referências geradas com IA nesta sessão e inspecionadas visualmente; o replay no script reutiliza essas referências. Prompts completos em `data/references/*.prompt.txt`.
- **651 fichas** incorporadas a LanceDB com vetores reais de 384 dimensões do modelo multilíngue. **603 candidatos** elegíveis a assets; 48 entradas promocionais excluídas da exportação.
- **16 testes Python** passaram, incluindo API com índice semântico real, falta de índice, IDs inválidos, faixas incompatíveis, água, predação, valores ausentes, cache, alteração de estilo e recuperação de saída ausente.
- **4 testes Node** passaram: equinócio, Fortaleza, dia/noite polares e ausência de geolocalização.
- Compilação Python e sintaxe dos scripts JavaScript verificadas.
- Prévia inspecionada no navegador: sprites visíveis, inclusão/remoção altera lista e Canvas, pausa altera controle para “Retomar”.
- API iniciada em localhost; consulta HTTP das três espécies registrada em `data/compatibility-smoke.json`.
- Preparação de pares executada: **2 treino / 1 validação**, separados por espécie científica. Dry-run da receita de treino registrado em `data/training-dry-run.json`.

O Python 3.9 do sistema emitiu aviso de LibreSSL/urllib3; a execução e os testes concluíram. Para instalação nova, usar Python 3.11 com ambiente virtual limpo.

## Ainda precisa de validação

- Chrome MV3 instalado: permissões opcionais, comunicação popup/service worker, `chrome.storage.local`, Shadow DOM na página e comportamento após reiniciar o navegador. A inspeção da prévia HTTP não substitui isso.
- CUDA: carregar pesos Qwen, gerar o smoke com o backend aberto, medir VRAM/latência e treinar LoRA com dataset suficiente.
- Avaliação de espécie inédita e continuidade de perspectiva/luz com o adaptador treinado.
- Lote integral: download das demais fotos, QA visual e release da extensão com os assets novos.
- Reavaliar a qualidade das fichas antes de usar o resultado para manejo de animais reais.

## Checklist para o Chrome

1. Carregar `extension` descompactada e iniciar `scripts/run_api.sh`.
2. Adicionar uma espécie, salvar com verificação e confirmar avisos de dados incompletos quando houver.
3. Adicionar/remover outra espécie; verificar que o resultado anterior não é reutilizado.
4. Abrir o aquário numa página HTTPS, arrastar, pausar, fechar e abrir novamente.
5. Reabrir popup e confirmar persistência.
6. Parar a API, alterar combinação e confirmar que a gravação é bloqueada com mensagem clara.
7. Negar localização e confirmar ciclo identificado como aproximado; depois permitir e conferir luz solar.
8. Confirmar bloqueio de injeção em páginas internas do Chrome com mensagem ao usuário.

As três espécies são exemplos visuais, não uma combinação biologicamente recomendada. O resultado usa incerteza porque as fichas não sustentam todos os critérios.
