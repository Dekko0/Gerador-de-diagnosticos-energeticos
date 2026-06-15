\NeedsTeXFormat{LaTeX2e}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%	Arquivo criado por Andre P. N. Tahim
%	Universidade Federal da Bahia
%	Laboratório de Eficiência Energética
%	07/01/2021
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\ProvidesClass{DIAG_PMS}[2021/01/07 Modelo Projeto de TCC Eng. Eletrica UFBA]
\LoadClass[
% -- opções da classe memoir --
12pt,				% tamanho da fonte
openany,			% capítulos começam em pág ímpar (insere página vazia caso preciso)
oneside,			% para impressão em recto e verso. Oposto a oneside
a4paper,			% tamanho do papel. 
% -- opções da classe abntex2 --
%chapter=TITLE,		% títulos de capítulos convertidos em letras maiúsculas
%section=TITLE,		% títulos de seções convertidos em letras maiúsculas
%subsection=TITLE,	% títulos de subseções convertidos em letras maiúsculas
%subsubsection=TITLE,% títulos de subsubseções convertidos em letras maiúsculas
% -- opções do pacote babel --
%english,			% idioma adicional para hifenização
%french,				% idioma adicional para hifenização
%spanish,			% idioma adicional para hifenização
brazil,				% o último idioma é o principal do documento
]{abntex2} % 12pt, frente e verso, cap. sempre inicia em pag. impar

% ---
% PACOTES
% ---

% ---
% Pacotes fundamentais 
% ---
\RequirePackage{lmodern}			% Usa a fonte Latin Modern
\RequirePackage[T1]{fontenc}		% Selecao de codigos de fonte.
\RequirePackage[utf8]{inputenc}		% Codificacao do documento (conversão automática dos acentos)
\RequirePackage{textcomp}			% Símbolos texto: \textmu \texttimes \textonehalf \textperiodcentered etc.
\RequirePackage{indentfirst}		% Indenta o primeiro parágrafo de cada seção.
\RequirePackage{color}				% Controle das cores
\RequirePackage{graphicx}			% Inclusão de gráficos
\RequirePackage{microtype} 			% para melhorias de justificação
\RequirePackage{amsmath}	
\RequirePackage{icomma}				% Vírgula como decimal 
\usepackage[printonlyused]{acronym} % Acrônimos
\usepackage[table]{xcolor}
\usepackage{float}     % no preâmbulo
\usepackage{colortbl}  % para cores de linha
\usepackage[table]{xcolor} % para \rowcolor
% ---

% ---
% Pacotes adicionais, usados no anexo do modelo de folha de identificação
% ---
\RequirePackage{multicol}
\RequirePackage{multirow}
% ---

% ---
% Pacotes adicionais, usados apenas no âmbito do Modelo Canônico do abnteX2
% ---
\RequirePackage{lipsum}				% para geração de dummy text
\RequirePackage{blindtext}				% para geração de dummy text
% ---

% ---
% Pacotes de citações
% ---
\RequirePackage[brazilian,hyperpageref]{backref}	 % Paginas com as citações na bibl
\RequirePackage[alf]{abntex2cite}	% Citações padrão ABNT
%\RequirePackage{showframe}

% --- 
% CONFIGURAÇÕES DE PACOTES
% --- 

% ---
% Configurações do pacote backref
\definecolor{azuluc}{RGB}{47, 84, 150} % cor de fundo igual à da imagem
% Usado sem a opção hyperpageref de backref
\renewcommand{\backrefpagesname}{Citado na(s) página(s):~}
% Texto padrão antes do número das páginas
\renewcommand{\backref}{}
% Define os textos da citação
\renewcommand*{\backrefalt}[4]{
	\ifcase #1 %
	Nenhuma citação no texto.%
	\or
	Citado na página #2.%
	\else
	Citado #1 vezes nas páginas #2.%
	\fi}%

% Comandos de dados - coorientador
\providecommand{\imprimirexaminadorIRotulo}{}
\providecommand{\imprimirexaminadorI}{}
\newcommand{\examinadorI}[2][\examinadorIname]%
{\renewcommand{\imprimirexaminadorIRotulo}{#1}%
	\renewcommand{\imprimirexaminadorI}{#2}}


% ---
\renewcommand{\imprimircapa}{%
	\begin{capa}%
		\center
		\noindent
        %\vspace{2cm}
		\begin{minipage}[b]{0.2\textwidth}    %% b or t, default is c
			\includegraphics[width=\linewidth]{./Figuras/ssa3}
		\end{minipage}%
		\begin{minipage}[b][2cm]{0.6\textwidth}
			\centering\bfseries\large
			{\ABNTEXchapterfont Relatório Técnico} \vfill
			{\ABNTEXchapterfont\large Diagnóstico Energético} \vfill
			{\ABNTEXchapterfont\large Prefeitura Municipal de Salvador}
		\end{minipage}%
		\begin{minipage}[b]{0.25\textwidth}
        %\vspace{-0.5cm}
			\includegraphics[width=\linewidth]{./Figuras/poup2}
		\end{minipage}\\
		\vfill
		{\ABNTEXchapterfont\large\imprimirautor}
		\vfill
		\begin{center}
			\ABNTEXchapterfont\bfseries\LARGE\imprimirtitulo
		\end{center}
		\vfill
		{\ABNTEXchapterfont\large\imprimirorientador}\\
		{\ABNTEXchapterfont\large\imprimircoorientador}
		\vfill
		{\ABNTEXchapterfont\imprimirlocal}\\
		{\ABNTEXchapterfont\imprimirdata}
		\vspace*{1cm}
	\end{capa}
}

\makeatletter
\renewcommand{\folhaderostocontent}{
	\begin{center}
		{\ABNTEXchapterfont\large\imprimirautor}
		\vspace*{\fill}
		\begin{center}
			\ABNTEXchapterfont\bfseries\Large\imprimirtitulo
		\end{center}
		\vspace*{\fill}
		\abntex@ifnotempty{\imprimirpreambulo}{%
			\hspace{.45\textwidth}
			\begin{minipage}{.5\textwidth}
				\SingleSpacing
				\imprimirpreambulo
			\end{minipage}%
			\vspace*{\fill}
		}%
		{\ABNTEXchapterfont\large\imprimirorientador\par}
		\abntex@ifnotempty{\imprimircoorientador}{%
			{\ABNTEXchapterfont\large\imprimircoorientador}%
		}%
	
		\vspace*{\fill}
		{\ABNTEXchapterfont\imprimirlocal}\par
		{\ABNTEXchapterfont\imprimirdata}
		\vspace*{1cm}
	\end{center}
}
\makeatother

% ---
% Configurações de aparência do PDF final

% alterando o aspecto da cor azul
\definecolor{blue}{RGB}{41,5,195}

% informações do PDF
\makeatletter
\hypersetup{
	%pagebackref=true,
	pdftitle={\@title}, 
	pdfauthor={\@author},
	pdfsubject={\imprimirpreambulo},
	pdfcreator={LaTeX with abnTeX2},
	pdfkeywords={abnt}{latex}{abntex}{abntex2}{relatório técnico}, 
	colorlinks=true,       		% false: boxed links; true: colored links
	linkcolor=blue,          	% color of internal links
	citecolor=blue,        		% color of links to bibliography
	filecolor=magenta,      		% color of file links
	urlcolor=blue,
	bookmarksdepth=4
}
\makeatother
% --- 

% --- 
% Espaçamentos entre linhas e parágrafos 
% --- 

% O tamanho da indetação do parágrafo é dado por:
\setlength{\parindent}{1.3cm}

% Controle do espaçamento entre um parágrafo e outro:
\setlength{\parskip}{0.2cm}  % tente também \onelineskip

% ---
% compila o indice
% ---
\makeindex
% ---
