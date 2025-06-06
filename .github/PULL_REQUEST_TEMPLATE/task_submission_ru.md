<!--
Требования к названию pull request:

"<Фамилия> <Имя>. Технология <TECHNOLOGY_NAME:SEQ|OMP|TBB|STL|MPI>. <Полное название задачи>. Вариант <Номер>"
-->

## Описание
<!--
Пожалуйста, предоставьте подробное описание вашей реализации, включая:
 - основные детали решения (описание выбранного алгоритма)
 - применение технологии параллелизма (если применимо)
-->

- **Задача**: _Введите здесь полное название задачи_
- **Вариант**: _Введите здесь номер варианта_
- **Технология**: _Введите технологию (например, SEQ, OMP, TBB, STL, MPI)_
- **Описание** вашей реализации и отчёта.  
  _Кратко опишите вашу реализацию и содержание отчёта здесь._

---

## Чек-лист
<!--
Пожалуйста, убедитесь, что следующие пункты выполнены **до** отправки pull request'а и запроса его ревью:
-->

- [ ] **Статус CI**: Все CI-задачи (сборка, тесты, генерация отчёта) успешно проходят на моей ветке в моем форке
- [ ] **Директория и именование задачи**: Я создал директорию с именем `<фамилия>_<первая_буква_имени>_<короткое_название_задачи>`
- [ ] **Полное описание задачи**: Я предоставил полное описание задачи в теле pull request
- [ ] **clang-format**: Мои изменения успешно проходят `clang-format` локально в моем форке (нет ошибок форматирования)
- [ ] **clang-tidy**: Мои изменения успешно проходят `clang-tidy` локально в моем форке (нет предупреждений/ошибок)
- [ ] **Функциональные тесты**: Все функциональные тесты успешно проходят локально на моей машине
- [ ] **Тесты производительности**: Все тесты производительности успешно проходят локально на моей машине
- [ ] **Ветка**: Я работаю в ветке, названной точно так же, как директория моей задачи (например, `nesterov_a_vector_sum`), а не в `master`
- [ ] **Правдивое содержание**: Я подтверждаю, что все сведения, указанные в этом pull request, являются точными и достоверными

<!--
ПРИМЕЧАНИЕ: Ложные сведения в этом чек-листе могут привести к отклонению PR и получению нулевого балла за соответствующую задачу.
-->
