import React from 'react';

import { HoldingsEditor } from '../../components/portfolio/HoldingsEditor';

export function EditHoldingsScreen({
  route,
  navigation
}: {
  route: any;
  navigation: any;
}) {
  return (
    <HoldingsEditor
      portfolioId={route.params.portfolioId}
      navigation={navigation}
    />
  );
}
