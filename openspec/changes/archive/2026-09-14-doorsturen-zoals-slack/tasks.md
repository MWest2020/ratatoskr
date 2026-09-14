# Taken

- [x] 1.1 `routing.py` om naar aanwijzen-op-id; `!route` blijft alias
- [x] 1.2 Tests: verzonnen id stuurt niets, dubbelzinnig voorvoegsel ook niet,
      notitie draagt de naam van de doorstuurder
- [x] 1.3 `prompts.route_clause(cfg)` uit de echte `routes`
- [x] 1.4 Bericht-ids in de prompt, alleen bij een agent die mag doorsturen
- [x] 1.5 Listener haakt beide in
- [x] 2.1 Live nagemeten door Mark, 2026-09-14 07:55. Odin stuurde een bestaand
      bericht uit #technical_debt door naar #bouw; de bronvermelding klopte
      (bronkanaal, oorspronkelijke schrijver, bericht-id `f45632ed3488`) en de
      inhoud stond in een blockquote.
      Het geweigerde geval is niet in de chat nagemeten — dat vraagt een agent
      die een verzonnen id noemt, en daar kun je niet op wachten. Het staat wél
      vast in `test_een_verzonnen_id_stuurt_niets`, en de weigeringsweg zelf
      (kanaal buiten het mandaat) is dezelfde code.
- [x] 2.2 Change archiveren
