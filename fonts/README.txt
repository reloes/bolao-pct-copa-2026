Fontes embarcadas no repo para a geração da imagem dos palpites (imagem.py).

Arquivos:
  DejaVuSans.ttf, DejaVuSans-Bold.ttf  — família DejaVu Sans

Por que estão aqui:
  No Streamlit Cloud as fontes do sistema nem sempre estão no caminho esperado;
  sem uma TTF garantida, o Pillow cai num font default que NÃO tem os glifos
  acentuados ("Ã") nem o travessão ("—"), e a imagem saía com caixas (□).
  Carregando esta fonte por caminho relativo (1ª da lista em imagem.py),
  a produção renderiza igual ao local.

Licença:
  DejaVu Fonts — derivada da Bitstream Vera (e Arev). Licença livre e
  redistribuível (inclusive em repositórios públicos), sem royalties.
  Detalhes: https://dejavu-fonts.github.io/License.html
  Cópia local obtida do pacote do LibreOffice (também redistribui a DejaVu).
