xgettext -L Python --from-code=utf-8 ./rest_food/*/*.py -o rest_food/locale/_common.po

msgmerge rest_food/locale/ru/LC_MESSAGES/messages.po rest_food/locale/_common.po -o rest_food/locale/ru/LC_MESSAGES/messages.po --lang=ru.UTF-8
msgmerge rest_food/locale/be/LC_MESSAGES/messages.po rest_food/locale/_common.po -o rest_food/locale/be/LC_MESSAGES/messages.po --lang=be.UTF-8

rm rest_food/locale/_common.po