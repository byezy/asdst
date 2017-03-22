import arcpy as ap
import arcpy.mapping as am
import os
import log
import ast
import utils
import configure


class Project(object):
    @log.log
    def __init__(self):

        self.title = None
        self.gdb = None
        self.mxd = am.MapDocument("CURRENT")
        self.df = None
        self.df = am.ListDataFrames(self.mxd)[0]
        self.gdb = None

        gdb = self.mxd.filePath.replace(".mxd", ".gdb")
        if ap.Exists(gdb):  # standard case, same name as mxd
            self.gdb = gdb
        else:  # mxd saved to a new name, go to tags
            tags = self.mxd.tags
            if tags:
                tag_list = tags.os.path.split(",")
                tag = [t for t in tag_list if (("ASDST" in t) and ("gdb" in t))]
                if tag:
                    tag = tag[0]
                    tag = tag.replace(";", ",")
                    tag = ast.literal_eval(tag)
                    gdb = tag.get("gdb", None)

                    if gdb and os.path.exists(gdb):
                        self.gdb = gdb

        return

    @log.log
    def valid(self):
        status = self.get_status()

        return False not in [c for a, b, c in status]

    @log.log
    def valid_gdb_and_srs(self):

        return utils.geodata_exists(self.gdb) and utils.get_dataframe_spatial_reference().factoryCode == 3308

    @log.log
    def get_status(self):

        result = []
        for k, v in configure.Configuration().layer_dictionary(self.gdb or "NONE").iteritems():
            result.append(utils.exists_return_tuple("description", v["1750_local"]))
            result.append(utils.exists_return_tuple("description", v["curr_local"]))

        result.append(["", "Dataframe spatial reference is GDA_1994_NSW_Lambert", self.df.spatialReference.name == "GDA_1994_NSW_Lambert"])

        return result

    @log.log
    def get_project_status(self):
        true = u"\u2714"
        false = u"\u2716"
        fmt = u"{} {}"

        s = self.get_status()

        uni = [[unicode(item), [false, true][value]] for desc, item, value in s]
        fmt_uni = [fmt.format(item, value) for item, value in uni]

        valid = False not in [value for desc, item, value in s]
        fmt_uni.append("THE PROJECT IS " + ["INVALID", "VALID"][valid])

        return "\n".join(fmt_uni)


class CreateProjectTool(object):

    class ToolValidator(object):
        """Class for validating a tool's parameter values and controlling
        the behavior of the tool's dialog."""

        def __init__(self, parameters):
            """Setup arcpy and the list of tool parameters."""
            self.params = parameters

        def initializeParameters(self):
            """Refine the properties of a tool's parameters.  This method is
            called when the tool is opened."""
            return

        def updateParameters(self):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""
            return

        def updateMessages(self):
            """Modify the messages created by internal validation for each tool
            parameter.  This method is called after internal validation."""
            return

    @log.log
    def __init__(self):

        return

    @log.log
    def getParameterInfo(self):

        # Name
        param_1 = ap.Parameter()
        param_1.name = u'Name'
        param_1.displayName = u'Name'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'

        # Description
        param_2 = ap.Parameter()
        param_2.name = u'Description'
        param_2.displayName = u'Description'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'

        # Parent_Directory
        param_3 = ap.Parameter()
        param_3.name = u'Parent_Directory'
        param_3.displayName = u'Parent Directory'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'Workspace'

        # # Project_Area
        # param_4 = ap.Parameter()
        # param_4.name = u'Project_Area'
        # param_4.displayName = u'Project Area'
        # param_4.parameterType = 'Required'
        # param_4.direction = 'Input'
        # param_4.datatype = u'GPFeatureRecordsetlayer'
        # param_4.value = configure.Configuration().empty_polyf_layer
        # try:
            # fc = ap.CreateFeatureclass_management("in_memory", "fc", "POLYGON")
            # efs = ap.MakeFeatureLayer_management(PROJECT.configuration.empty_featureset_layer, "efs")
            # efs.replaceDataSource(fc)  # p, "FILEGDB_WORKSPACE", n, validate=False)
            # efs = am.Layer(PROJECT.configuration.empty_featureset_layer)
            # # param_4.value = u'in_memory\\{714ADB01-ECAF-44AD-9CE1-0DE3ECF49BBB}'
            # param_4.value = r"C:\Data\asdst\asdst_addin\Install\epf.lyr" # PROJECT.configuration.empty_polyf_layer
            # param_4.value = PROJECT.configuration.empty_featureset_layer  #efs
        # except:
        #     pass

        return [param_1, param_2, param_3]

    @log.log
    def isLicensed(self):
        return True

    @log.log
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
            return validator(parameters).updateParameters()

    @log.log
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
            return validator(parameters).updateMessages()

    @log.log
    def execute(self, parameters, messages):

        # add_message = messages.addMessage
        # add_error = messages.addErrorMessage

        # Get user inputs
        raw_title = parameters[0].valueAsText  # title
        description = parameters[1].valueAsText  # description
        directory = parameters[2].valueAsText  # parent directory
        # geometry = parameters[3].value  # geometry (feature set)

        sane_title = raw_title.lower().replace(" ", "_")
        base = os.path.join(directory, sane_title)
        mxd_file = base + ".mxd"
        gdb = base + ".gdb"

        config = configure.Configuration()
        # layer_dict = config.layer_dictionary(gdb)

        messages.addMessage("Creating project geodatabase '{}'".format(gdb))
        ap.Copy_management(config.template_project_gdb, gdb)

        messages.addMessage("Creating project map document '{}'".format(mxd_file))
        ap.Copy_management(config.template_mxd, mxd_file)

        # Fix default MXD tags
        messages.addMessage("Fixing mxd tags")
        mxd = ap.mapping.MapDocument(mxd_file)
        mxd.title = raw_title
        tag = {"ASDST": "DO NOT EDIT THIS TAG",
               "Version": 7,
               "Title": sane_title,
               "mxd": mxd_file,
               "gdb": gdb,
               "Description": description}
        tag = str(tag).replace(",", ";")
        mxd.tags = ",".join([mxd.tags, tag])

        # # Import project areas into project workspace i.e. save the geometry to be used
        # add_message("Importing areas")
        # area = os.path.join(gdb, "project_area")
        # try:
        #     # might be a feature set
        #     geometry.save(area)
        #     add_message("\tTemporary feature set imported to {}".format(area))
        # except:
        #     try:
        #         # or might be a layer
        #         ap.CopyFeatures_management(geometry, area)
        #         add_message("\tFeature layer imported to {}".format(area))
        #     except Exception as e:
        #         # or fuck knows what it is
        #         add_error("Error copying project area feature {0}".format(e.message))
        #         raise ap.ExecuteError
        #
        # # Build data
        # add_message("Building data")
        # layer_dict2 = {}
        #
        # add_message("\tClipping model reliability layer")
        # n = "drvd_rel"
        # src = os.path.join(config.source_fgdb, n)
        # lcl = os.path.join(gdb, n)
        # add_message("\t\t{}\t{} --> {}".format(n, src, lcl))
        # ap.Clip_management(src, "#", lcl, area, "#", "ClippingGeometry")
        # layer_dict2["reliability"] = lcl
        #
        # add_message("\tClipping survey priority layer")
        # lcl = os.path.join(gdb, "drvd_srv")
        # src = os.path.join(config.source_fgdb, "drvd_srv")
        # add_message("\t\tdrvd_srv\t{} --> {}".format(src, lcl))
        # ap.Clip_management(src, "#", lcl, area, "#", "ClippingGeometry")
        # layer_dict2["priority"] = lcl
        #
        # add_message("\tClipping regionalisation layers")
        # for i in range(1, 5):
        #     n = "aslu_lvl{0}".format(i)
        #     src = os.path.join(config.source_fgdb, n)
        #     lcl = os.path.join(gdb, n)
        #     add_message("\t\t{}\t{} --> {}".format(n, src, lcl))
        #     ap.Clip_analysis(src, area, lcl)
        #     layer_dict2[n] = lcl
        #
        # add_message("\tClipping 1750 layers")
        # for k, v in layer_dict.iteritems():
        #     lyr = v["name"]
        #     src, lcl = v["1750_source"], v["1750_local"]
        #     add_message("\t\t{}\t{} --> {}".format(lyr, src, lcl))
        #     ap.Clip_management(src, "#", lcl, area, "#", "ClippingGeometry")
        #     ap.BuildRasterAttributeTable_management(lcl, "Overwrite")
        #     try:  # wrap this: it fails if the raster contains only 0's (SHL)
        #         ap.CalculateStatistics_management(lcl)
        #     except:
        #         pass
        #
        # add_message("Calculating current layers")
        # src = os.path.join(config.source_fgdb, "cu_param3")
        # lup = os.path.join(gdb, "cu_param3")
        # ap.Clip_management(src, "#", lup, area, "#", "ClippingGeometry")
        # loss_rasters = {}
        # env.workspace = gdb
        # for k, v in layer_dict.iteritems():
        #     add_message("\t\t{0}".format(v["name"]))
        #     ras_par = ap.sa.Lookup(lup, k)  # lcl_lup_ras, k)
        #     ras_1750 = ap.Raster(v["1750_local"])
        #     ras_curr = ap.sa.Int((ras_par / 100.0) * ras_1750)
        #     lcl = v["curr_local"]
        #     ras_curr.save(lcl)
        #     ras_loss = ap.sa.Minus(ras_1750, ras_curr)
        #     ras_loss.save(os.path.join(gdb, "loss_{0}".format(k.lower())))
        #     loss_rasters[v["name"]] = ras_loss.catalogPath
        #     ap.BuildRasterAttributeTable_management(lcl, "Overwrite")
        #     try:  # wrap this: it fails if the raster contains only 0's (SHL)
        #         ap.CalculateStatistics_management(lcl)
        #     except:
        #         pass
        #     del ras_curr, ras_1750, ras_loss, ras_par
        #
        # add_message("\tCalculating accumulated impact")
        # t_ras = None
        # for k, ras in loss_rasters.iteritems():
        #     add_message("\t...{0}".format(k))
        #     t_ras = ap.Raster(ras)
        #     if t_ras is not None:
        #         t_ras += t_ras
        # acc_ds = os.path.join(gdb, "acc_impact_unscaled")
        # t_ras.save(acc_ds)
        # ap.BuildRasterAttributeTable_management(t_ras, "Overwrite")
        # try:
        #     ap.CalculateStatistics_management(t_ras)
        # except:
        #     pass
        # minv = int(ap.GetRasterProperties_management(t_ras, "MINIMUM").getOutput(0))
        # maxv = int(ap.GetRasterProperties_management(t_ras, "MAXIMUM").getOutput(0))
        # # Rescaled grid = [(grid - Min value from grid) * (Max scale value - Min scale value) / (Max value from grid - Min value from grid)] + Min scale value
        # t_ras_2 = (t_ras - minv) * (1000 - 0) / (maxv - minv)
        # acc_ds = os.path.join(gdb, "acc_impact_scaled")
        # t_ras_2.save(acc_ds)
        # del t_ras, t_ras_2
        # layer_dict2["impact"] = acc_ds
        #
        # add_message("\tCalculating loss")
        # loss = os.path.join(gdb, "project_loss")
        # ic = ap.da.InsertCursor(loss, "*")
        # n = 0
        # for k, v in layer_dict.iteritems():
        #     add_message("\t\t{0}".format(v["name"]))
        #     n += 1
        #     sum_1750 = ap.RasterToNumPyArray(v["1750_local"], nodata_to_value=0).sum()
        #     sum_curr = ap.RasterToNumPyArray(v["curr_local"], nodata_to_value=0).sum()
        #     sum_change = (sum_curr - sum_1750)
        #     if sum_curr == 0 and sum_1750 == 0:
        #         loss_val = 0
        #     elif sum_change == sum_1750:
        #         loss_val = 100
        #     else:
        #         loss_val = int((sum_1750 - sum_curr) * 100.0 / sum_1750)
        #     vals = (n, k, v["name"], sum_1750, sum_curr, sum_change, loss_val)
        #     ic.insertRow(vals)
        # del ic
        #
        # # Compact the FGDB workspace
        # add_message(utils.compact_fgdb(gdb))
        #
        # # Add data to map
        # add_message("Adding data layers to map...")
        # utils.add_table_to_mxd(mxd, loss)
        #
        # lyrs = {"Model Reliability": layer_dict2["reliability"]}
        # utils.add_layers_to_mxd(mxd, lyrs, "Derived", "relia", config)
        #
        # lyrs = {"Survey Priority": layer_dict2["priority"]}
        # utils.add_layers_to_mxd(mxd, lyrs, "Derived", "prior", config)
        #
        # lyrs = {"Accumulated Impact": layer_dict2["impact"]}
        # utils.add_layers_to_mxd(mxd, lyrs, "Derived", "accim", config)
        #
        # lyrs = {"Regionalisation Level {0}".format(i): layer_dict2["aslu_lvl{0}".format(i)] for i in range(1, 5)}
        # utils.add_layers_to_mxd(mxd, lyrs, "Regionalisation", "regio", config)
        #
        # lyrs = {v["name"]: v["1750_local"] for k, v in layer_dict.iteritems()}
        # utils.add_layers_to_mxd(mxd, lyrs, "Pre-1750", "model", config)
        #
        # lyrs = {v["name"]: v["curr_local"] for k, v in layer_dict.iteritems()}
        # utils.add_layers_to_mxd(mxd, lyrs, "Current", "model", config)

        # Save and report status
        mxd.save()
        messages.addMessage("New ASDST project '{0}' is launching in a new ArcMap window".format(raw_title))

        # Launch new MXD
        os.system(mxd_file)


def main():
    return

if __name__ == '__main__':
    main()
