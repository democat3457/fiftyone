import { Route } from "@fiftyone/components";
import { NotFoundError } from "@fiftyone/utilities";
import React, { useEffect } from "react";
import { graphql, usePreloadedQuery } from "react-relay";

import DatasetComponent from "../../components/Dataset";
import { useStateUpdate } from "../../utils/hooks";
import { DatasetQuery } from "./__generated__/DatasetQuery.graphql";
import { datasetName } from "../../recoil/selectors";
import { useRecoilValue } from "recoil";
import transformDataset from "./transformDataset";

const Query = graphql`
  query DatasetQuery($name: String!, $view: JSONArray) {
    dataset(name: $name, view: $view) {
      id
      name
      mediaType
      sampleFields {
        ftype
        subfield
        embeddedDocType
        path
        dbField
      }
      frameFields {
        ftype
        subfield
        embeddedDocType
        path
        dbField
      }
      appSidebarGroups {
        name
        paths
      }
      maskTargets {
        name
        targets {
          target
          value
        }
      }
      defaultMaskTargets {
        target
        value
      }
      evaluations {
        key
        version
        timestamp
        viewStages
        config {
          cls
          predField
          gtField
        }
      }
      brainMethods {
        key
        version
        timestamp
        viewStages
        config {
          cls
          embeddingsField
          method
          patchesField
        }
      }
      lastLoadedAt
      createdAt
      version
    }
  }
`;

export const Dataset: Route<DatasetQuery> = ({ prepared }) => {
  const { dataset } = usePreloadedQuery(Query, prepared);
  const name = useRecoilValue(datasetName);

  if (!dataset) {
    throw new NotFoundError(window.location.pathname);
  }

  const update = useStateUpdate();

  useEffect(() => {
    update({
      dataset: transformDataset(dataset),
    });
  }, [dataset]);

  if (!name) {
    return null;
  }

  return <DatasetComponent />;
};

export default Dataset;